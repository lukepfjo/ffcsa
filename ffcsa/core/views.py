import datetime
import stripe
from copy import deepcopy

from cartridge.shop import views as s_views
from cartridge.shop.forms import CartItemFormSet, DiscountForm
from cartridge.shop.models import Category, Order
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.messages import error, success, info
from django.contrib.sites.models import Site
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse, HttpResponse
from django.urls import reverse
from django.utils import formats
from django.utils.http import is_safe_url
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from mezzanine.conf import settings
from mezzanine.utils.email import send_mail_template
from mezzanine.utils.views import paginate

from ffcsa.core.forms import CartDinnerForm, wrap_AddProductForm, ProfileForm
from ffcsa.core.models import Payment
from ffcsa.core.subscriptions import create_stripe_subscription, send_failed_payment_email, send_first_payment_email, \
    SIGNUP_DESCRIPTION, clear_ach_payment_source, send_subscription_canceled_email, send_pending_payment_email, \
    update_stripe_subscription
from .utils import ORDER_CUTOFF_DAY, get_order_total, get_payment_total, get_friday_pickup_date, next_weekday, \
    get_order_week_start

stripe.api_key = settings.STRIPE_SECRET_KEY


def shop_home(request, template="shop_home.html"):
    root_categories = Category.objects.published().filter(parent__isnull=True)

    context = {
        'categories': root_categories,
        'settings': settings,
    }

    return TemplateResponse(request, template, context)


@never_cache
def cart(request, template="shop/cart.html",
         cart_formset_class=CartItemFormSet,
         discount_form_class=DiscountForm,
         extra_context={}):
    cart_dinner_form = CartDinnerForm(request, request.POST or None)

    if request.method == "POST":
        if cart_dinner_form.is_valid():
            cart_dinner_form.save()

    extra_context['cart_dinner_form'] = cart_dinner_form
    extra_context['dinner_week'] = get_friday_pickup_date().day <= 7

    return s_views.cart(request, template=template, cart_formset_class=cart_formset_class,
                        discount_form_class=discount_form_class, extra_context=extra_context)


# monkey patch the product view
original_product_view = deepcopy(s_views.product)


def product(request, slug, template="shop/product.html", extra_context=None, **kwargs):
    """
    extends cartridge shop product view, only allowing authenticated users to add products to the cart
    """
    if request.method == 'POST':
        if not request.user.is_authenticated():
            raise Exception("You must be authenticated in order to add products to your cart")
        if not request.cart.user_id:
            request.cart.user_id = request.user.id
        elif request.cart.user_id != request.user.id:
            raise Exception("Server Error")

    form_class = wrap_AddProductForm(request.cart)
    response = original_product_view(request, slug, template=template, form_class=form_class,
                                     extra_context=extra_context)

    if isinstance(response, HttpResponseRedirect):
        request.method = 'GET'
        return original_product_view(request, slug, template=template, form_class=form_class,
                                     extra_context=extra_context, **kwargs)

    return response


s_views.product = product


def signup(request, template="accounts/account_signup.html",
           extra_context=None):
    """
    signup view.
    """
    form = ProfileForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        new_user = form.save()
        info(request, "Successfully signed up")
        auth_login(request, new_user)

        c = {
            'user': "{} {}".format(new_user.first_name, new_user.last_name),
            'user_url': request.build_absolute_uri(reverse("admin:auth_user_change", args=(new_user.id,))),
            'drop_site': form.cleaned_data['drop_site'],
            'phone_number': form.cleaned_data['phone_number'],
            'phone_number_2': form.cleaned_data['phone_number_2'],
            'best_time_to_reach': form.cleaned_data['best_time_to_reach'],
            'communication_method': form.cleaned_data['communication_method'],
            'family_stats': form.cleaned_data['family_stats'],
            'hear_about_us': form.cleaned_data['hear_about_us'],
            'payments_url': request.build_absolute_uri(reverse("payments")),
        }

        send_mail_template(
            "New User Signup %s" % settings.SITE_TITLE,
            "ffcsa_core/send_admin_new_user_email",
            settings.DEFAULT_FROM_EMAIL,
            settings.ACCOUNTS_APPROVAL_EMAILS,
            context=c,
            fail_silently=True,
        )
        send_mail_template(
            "Congratulations on your new Full Farm CSA account!",
            "ffcsa_core/send_new_user_email",
            settings.DEFAULT_FROM_EMAIL,
            new_user.email,
            fail_silently=False,
            addr_bcc=[settings.EMAIL_HOST_USER]
        )

        return HttpResponseRedirect(reverse('payments'))

    context = {"form": form, "title": "Join Now!"}
    context.update(extra_context or {})
    return TemplateResponse(request, template, context)


@login_required
def order_history(request, template="shop/order_history.html"):
    ytd_order_total = get_order_total(request.user)
    ytd_payment_total = get_payment_total(request.user)

    extra_context = {
        'ytd_contrib': '{0:.2f}'.format(ytd_payment_total),
        'ytd_ordered': ytd_order_total,
        'budget': '{0:.2f}'.format(ytd_payment_total - ytd_order_total)
    }

    return s_views.order_history(request, template=template, extra_context=extra_context)


@login_required
def payments(request, template="ffcsa_core/payments.html", extra_context={}):
    """
    Display a list of the currently logged-in user's past orders.
    """
    next_payment_date = None
    if request.user.profile.stripe_subscription_id:
        subscription = stripe.Subscription.retrieve(request.user.profile.stripe_subscription_id)
        next_payment_date = datetime.date.fromtimestamp(subscription.current_period_end + 1)
        next_payment_date = formats.date_format(next_payment_date, "D, F d")

    all_payments = Payment.objects.filter(user__id=request.user.id)
    payments = paginate(all_payments.order_by('-date', '-id'),
                        request.GET.get("page", 1),
                        settings.SHOP_PER_PAGE_CATEGORY,
                        settings.MAX_PAGING_LINKS)
    context = {"payments": payments,
               "contact_email": settings.DEFAULT_FROM_EMAIL,
               "next_payment_date": next_payment_date,
               "subscribe_errors": request.GET.getlist('error'),
               "STRIPE_API_KEY": settings.STRIPE_API_KEY}
    context.update(extra_context or {})
    return TemplateResponse(request, template, context)


@require_POST
@login_required
def payments_subscribe(request):
    """
    Create a new subscription
    """
    errors = []
    amount = Decimal(request.POST.get('amount'))
    paymentType = request.POST.get('paymentType')
    stripeToken = request.POST.get('stripeToken')

    user = request.user
    if not user.profile.paid_signup_fee and not request.POST.get('signupAcknowledgement') == 'True':
        errors.append('You must acknowledge the 1 time signup fee')

    if not stripeToken:
        errors.append('Invalid Request')

    try:
        if not errors:
            if paymentType == 'CC':
                if not user.profile.stripe_customer_id:
                    customer = stripe.Customer.create(
                        email=user.email,
                        description=user.get_full_name(),
                        source=stripeToken,
                    )
                    user.profile.stripe_customer_id = customer.id
                else:
                    customer = stripe.Customer.retrieve(user.profile.stripe_customer_id)
                    customer.source = stripeToken
                    customer.save()
                user.profile.payment_method = 'CC'
                user.profile.monthly_contribution = amount
                user.profile.save()

                # we can create the subscription right now
                create_stripe_subscription(user)
                success(request,
                        'Your subscription has been created and your first payment is pending. '
                        'You should see the payment credited to your account within the next few minutes')
            elif paymentType == 'ACH':
                if not user.profile.stripe_customer_id:
                    customer = stripe.Customer.create(
                        email=user.email,
                        description=user.get_full_name(),
                        source=stripeToken,
                    )
                    user.profile.stripe_customer_id = customer.id
                else:
                    customer = stripe.Customer.retrieve(user.profile.stripe_customer_id)
                    customer.source = stripeToken
                    customer.save()
                user.profile.payment_method = 'ACH'
                user.profile.monthly_contribution = amount
                user.profile.ach_status = 'VERIFIED' if customer.sources.data[0].status == 'verified' else 'NEW'
                user.profile.save()
                success(request,
                        'Your subscription has been created. You will need to verify your bank account '
                        'before your first payment is made.')
            else:
                errors.append('Unknown Payment Type')
    except stripe.error.CardError as e:
        body = e.json_body
        err = body.get('error', {})
        errors.append(err.get('message'))

    url = reverse('payments')
    isFirst = True
    for error in errors:
        if isFirst:
            url += "?error={}".format(error)
        else:
            url += "&error={}".format(error)

    return HttpResponseRedirect(url)


@require_POST
@login_required
def payments_update(request):
    """
    Update a payment source
    """
    errors = []
    paymentType = request.POST.get('paymentType')
    stripeToken = request.POST.get('stripeToken')

    user = request.user
    if not user.profile.stripe_customer_id or not user.profile.stripe_subscription_id:
        errors.append(
            'Could not find your subscription id to update. Please contact the site administrator.')

    if not stripeToken:
        errors.append('Invalid Request')

    try:
        if not errors:
            if paymentType == 'CC':
                customer = stripe.Customer.retrieve(user.profile.stripe_customer_id)
                customer.source = stripeToken
                customer.save()
                user.profile.ach_status = None  # reset this so they don't receive error msg for failed ach verification
                user.profile.save()
                success(request, 'Your payment method has been updated.')
            elif paymentType == 'ACH':
                customer = stripe.Customer.retrieve(user.profile.stripe_customer_id)
                customer.source = stripeToken
                customer.save()
                user.profile.ach_status = 'VERIFIED' if customer.sources.data[0].status == 'verified' else 'NEW'
                user.profile.save()
                success(request, 'Your payment method has been updated.')
            else:
                errors.append('Unknown Payment Type')
    except stripe.error.CardError as e:
        body = e.json_body
        err = body.get('error', {})
        errors.append(err.get('message'))

    url = reverse('payments')
    isFirst = True
    for error in errors:
        if isFirst:
            url += "?error={}".format(error)
        else:
            url += "&error={}".format(error)

    return HttpResponseRedirect(url)


@require_POST
@login_required
def payments_update_amount(request):
    """
    Update subscription amount
    """
    errors = []
    amount = Decimal(request.POST.get('amount'))

    user = request.user
    if not user.profile.stripe_customer_id or not user.profile.stripe_subscription_id:
        errors.append(
            'Could not find your subscription id to update. Please contact the site administrator.')

    if not errors and amount != user.profile.monthly_contribution:
        user.profile.monthly_contribution = amount
        update_stripe_subscription(user)
        user.profile.save()
        success(request, 'Your monthly contribution has been updated.')

    url = reverse('payments')
    isFirst = True
    for error in errors:
        if isFirst:
            url += "?error={}".format(error)
        else:
            url += "&error={}".format(error)

    return HttpResponseRedirect(url)


@require_POST
@login_required
def make_payment(request):
    """
    Make a 1 time payment
    """
    hasError = False
    amount = Decimal(request.POST.get('amount'))

    user = request.user
    if not user.profile.stripe_customer_id:
        hasError = True
        error(request, 'Could not find a valid customer id. Please contact the site administrator.')

    if not request.POST.get('chargeAcknowledgement') == 'True':
        hasError = True
        error(request, 'You must acknowledge the charge')

    if not amount:
        hasError = True
        error(request, 'Invalid amount provided.')

    if amount < 20:
        hasError = True
        error(request, 'Minimum payment amount is $20.')

    try:
        if not hasError:
            stripeToken = request.POST.get('stripeToken')
            card = None
            if stripeToken:
                customer = stripe.Customer.retrieve(user.profile.stripe_customer_id)
                card = customer.sources.create(source=stripeToken)

            stripe.Charge.create(
                amount=(amount * 100).quantize(0),  # in cents
                currency='usd',
                description='FFCSA Payment',
                customer=user.profile.stripe_customer_id,
                source=card.id if card else None,
                statement_descriptor='FFCSA Payment'
            )
            success(request, 'Your payment is pending.')
            # Payment will be created when the charge is successful
    except stripe.error.CardError as e:
        body = e.json_body
        err = body.get('error', {})
        error(request, err.get('message'))

    return HttpResponseRedirect(reverse('payments'))


@require_POST
@login_required
def donate(request):
    """
    Make a 1 donation to the feed a friend fund
    """
    hasError = False
    amount = Decimal(request.POST.get('amount'))

    user = request.user
    if not amount:
        hasError = True
        error(request, 'Invalid amount provided.')

    if amount > Decimal(request.session["remaining_budget"]):
        hasError = True
        error(request, 'You can not donate more then your remaining budget.')

    if not hasError:
        feed_a_friend, created = User.objects.get_or_create(username=settings.FEED_A_FRIEND_USER)

        order_dict = {
            'user_id': user.id,
            'time': datetime.datetime.now(),
            'site': Site.objects.get(id=1),
            'billing_detail_first_name': user.first_name,
            'billing_detail_last_name': user.last_name,
            'billing_detail_email': user.email,
            'billing_detail_phone': user.profile.phone_number,
            'billing_detail_phone_2': user.profile.phone_number_2,
            'total': amount,
        }

        order = Order.objects.create(**order_dict)

        item_dict = {
            'sku': 0,
            'description': 'Feed-A-Friend Donation',
            'quantity': 1,
            'unit_price': amount,
            'total_price': amount,
            'category': 'Feed-A-Friend',
            'vendor': 'Feed-A-Friend',
            'vendor_price': amount,
        }

        order.items.create(**item_dict)
        Payment.objects.create(amount=amount, user=feed_a_friend, notes="Donation from {}".format(user.get_full_name()))
        success(request, 'Thank you for your donation to the Feed-A-Friend fund!')

    next = request.GET.get('next', '/')
    # check that next is safe
    if not is_safe_url(next):
        next = '/'
    return HttpResponseRedirect(next)


@require_POST
@login_required
def verify_ach(request):
    """
    Verify an ACH bank account
    """
    errors = []
    amount1 = request.POST.get('amount1')
    amount2 = request.POST.get('amount2')
    user = request.user

    if not amount1 or not amount2:
        errors.append('both amounts are required')

    if not user.profile.stripe_customer_id:
        errors.append('You are missing a customerId. Please contact the site administrator')

    if not errors:
        customer = stripe.Customer.retrieve(user.profile.stripe_customer_id)
        bank_account = customer.sources.retrieve(customer.default_source)

        amount1 = amount1.split('.')[-1]
        amount2 = amount2.split('.')[-1]

        # verify the account
        try:
            bank_account.verify(amounts=[amount1, amount2])
            user.profile.ach_status = 'VERIFIED'
            user.profile.save()

            # we can create the subscription right now
            if not user.profile.stripe_subscription_id:
                create_stripe_subscription(user)
                if not Payment.objects.filter(user=user).exists():
                    success(request,
                            'Your account has been verified and your first payment is processing. '
                            'When your payment has been received, you will receive an email letting '
                            'you know when your first ordering and pickup dates are. If you do not '
                            'see this email in the next 5 - 7 business days, please check your spam')
                else:
                    subscription = stripe.Subscription.retrieve(user.profile.stripe_subscription_id)
                    next_payment_date = datetime.date.fromtimestamp(subscription.current_period_end + 1)
                    next_payment_date = formats.date_format(next_payment_date, "D, F d")
                    success(request,
                            'Congratulations, your account has been verified and your first payment is processing. '
                            'You will be seeing this amount show up in your member store account in 5 - 7 business '
                            'days. Your next scheduled payment will be ' + next_payment_date)
            else:
                success(request, 'Your account has been verified.')
        except stripe.error.CardError as e:
            user.profile.ach_status = 'VERIFYING'
            user.profile.save()
            body = e.json_body
            err = body.get('error', {})
            error(request, err.get('message'))

    url = reverse('payments')
    isFirst = True
    for error in errors:
        if isFirst:
            url += "?error={}".format(error)
        else:
            url += "&error={}".format(error)

    return HttpResponseRedirect(url)


@require_POST
@csrf_exempt
def stripe_webhooks(request):
    """
    endpoint for handling stripe webhooks
    """
    # Retrieve the request's body and parse it as JSON:
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_ENDPOINT_SECRET
        )

        if event.type == 'charge.pending':
            user = User.objects.filter(profile__stripe_customer_id=event.data.object.customer).first()
            charge = event.data.object
            # only save pending ach transfers. cc payments are basically instant
            if user and charge.source.object == 'bank_account':
                amount = charge.amount / 100  # amount is in cents
                date = datetime.datetime.fromtimestamp(charge.created)
                existing_payments = Payment.objects.filter(user=user, amount=amount, date=date)
                if existing_payments.exists():
                    raise AssertionError(
                        "Pending Payment Error: That payment already exists: {}".format(existing_payments.first()))
                else:
                    payment = Payment.objects.create(user=user, amount=amount, date=date, pending=True)
                    payment.save()
                    payments_url = request.build_absolute_uri(reverse("payments"))
                    send_pending_payment_email(user, payments_url)
        elif event.type == 'charge.succeeded':
            user = User.objects.filter(profile__stripe_customer_id=event.data.object.customer).first()
            charge = event.data.object
            if user:
                if charge.description == SIGNUP_DESCRIPTION:
                    user.profile.paid_signup_fee = True
                    user.profile.save()
                else:
                    amount = charge.amount / 100  # amount is in cents
                    date = datetime.datetime.fromtimestamp(charge.created)
                    existing_payments = Payment.objects.filter(user=user, amount=amount, date=date)
                    if existing_payments.filter(pending=False).exists():
                        raise AssertionError(
                            "That payment already exists: {}".format(existing_payments.filter(pending=False).first()))
                    else:
                        sendFirstPaymentEmail = not Payment.objects.filter(user=user).exists()
                        payment = existing_payments.filter(pending=True).first()
                        if payment is None:
                            payment = Payment.objects.create(user=user, amount=amount, date=date)
                        else:
                            payment.pending = False
                        payment.save()
                        if sendFirstPaymentEmail:
                            user.profile.start_date = date
                            user.profile.save()
                            send_first_payment_email(user)
        elif event.type == 'charge.failed':
            user = User.objects.filter(profile__stripe_customer_id=event.data.object.customer).first()
            charge = event.data.object
            err = charge.failure_message
            payments_url = request.build_absolute_uri(reverse("payments"))
            created = datetime.datetime.fromtimestamp(charge.created).strftime('%d-%m-%Y')
            send_failed_payment_email(user, err, charge.amount / 100, created, payments_url)
        elif event.type == 'customer.source.updated' and event.data.object.object == 'bank_account':
            user = User.objects.filter(profile__stripe_customer_id=event.data.object.customer).first()
            if user.profile.ach_status == 'NEW' and event.data.object.status == 'verification_failed':
                # most likely wrong account info was entered
                clear_ach_payment_source(user, event.data.object.id)
        elif event.type == 'customer.subscription.deleted':
            user = User.objects.filter(profile__stripe_customer_id=event.data.object.customer).first()
            user.profile.stripe_subscription_id = None
            user.profile.save()
            date = datetime.datetime.fromtimestamp(event.data.object.canceled_at).strftime('%d-%m-%Y')
            payments_url = request.build_absolute_uri(reverse("payments"))
            send_subscription_canceled_email(user, date, payments_url)



    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Do something with event

    return HttpResponse(status=200)


#############
# Custom Admin Views
#############

@staff_member_required
def admin_attending_dinner(request, template="admin/attending_dinner.html"):
    today = datetime.date.today()

    if today.weekday() < ORDER_CUTOFF_DAY:
        delta = ORDER_CUTOFF_DAY - today.weekday()
        order_date = today + datetime.timedelta(delta) - datetime.timedelta(7)
    else:
        delta = today.weekday() - ORDER_CUTOFF_DAY
        order_date = today - datetime.timedelta(delta)

    last_week_orders = Order.objects \
        .filter(time__gte=order_date).order_by('billing_detail_last_name')

    attendees = [{'family': o.billing_detail_last_name, 'attending_dinner': o.attending_dinner}
                 for o in last_week_orders if o.attending_dinner > 0]

    context = {
        'attendees': attendees
    }

    return TemplateResponse(request, template, context)


User = get_user_model()


@staff_member_required
def admin_member_budgets(request, template="admin/member_budgets.html"):
    users = User.objects.filter(is_active=True).order_by('last_name')

    budgets = []

    for user in users:
        ytd_contrib = get_payment_total(user)
        ytd_ordered = get_order_total(user)
        if not ytd_ordered:
            ytd_ordered = Decimal(0)
        if not ytd_contrib:
            ytd_contrib = Decimal(0)
        budgets.append({
            'user': user,
            'ytd_contrib': "{0:.2f}".format(ytd_contrib),
            'ytd_ordered': ytd_ordered,
            'budget': "{0:.2f}".format(ytd_contrib - ytd_ordered)
        })

    context = {
        'budgets': budgets
    }

    return TemplateResponse(request, template, context)


@staff_member_required
def member_order_history(request, template="admin/member_order_history.html"):
    users = User.objects.filter(is_active=True).order_by('last_name')

    data = []

    next_order_day = next_weekday(get_order_week_start(), ORDER_CUTOFF_DAY)  # get the order day

    wk = next_order_day - datetime.timedelta(7)
    weeks = [wk]

    # go back 8 weeks
    while wk > next_order_day - datetime.timedelta(8 * 7):
        wk = wk - datetime.timedelta(7)
        weeks.append(wk)

    weeks.reverse()

    for user in users:
        orders = Order.objects.filter(user_id=user.id, time__gte=datetime.datetime(wk.year, wk.month, wk.day)).order_by('time')
        sum = 0
        num_orders = 0

        order_totals = []

        i = 0
        for order in orders:
            while weeks[i].date() < order.time.date():
                order_totals.append(0)
                i += 1

            if weeks[i].date() == order.time.date():
                order_totals.append(order.total.quantize(Decimal('.00')))
                sum += order.total
                num_orders += 1
            else:
                order_totals.append(0)

            i += 1

        while len(order_totals) < len(weeks):
            order_totals.append(0)

        data.append({
            'user': user,
            'orders': order_totals,
            'avg': 0 if sum == 0 else Decimal(sum / num_orders).quantize(Decimal('.00'))
        })

    context = {
        'data': data,
        'weeks': weeks
    }

    return TemplateResponse(request, template, context)


@csrf_protect
@staff_member_required
def admin_bulk_payments(request, template="admin/bulk_payments.html"):
    new_month = request.GET.get('newMonth', False)
    ids = request.GET.get('ids', [])
    if ids and isinstance(ids, str):
        ids = ids.split(',')

    if new_month:
        users = User.objects.filter(
            ~Q(profile__monthly_contribution__isnull=True) & ~Q(profile__monthly_contribution=0),
            is_active=True, profile__stripe_subscription_id__isnull=True).order_by(
            'last_name')
        extra = users.count() + 1
        can_delete = True
    else:
        extra = 1 if len(ids) > 0 else 2
        can_delete = len(ids) > 0

    PaymentFormSet = modelformset_factory(Payment, fields=('user', 'date', 'amount', 'notes'), can_delete=can_delete,
                                          extra=extra)

    if request.method == 'POST':
        formset = PaymentFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(reverse('admin:ffcsa_core_payment_changelist'))

    if new_month:
        formset = PaymentFormSet(queryset=Payment.objects.none())

        i = 0
        for user in users:
            form = formset.forms[i]
            form.initial = {
                'amount': user.profile.monthly_contribution,
                'user': user.id
            }
            i += 1
    else:
        PaymentFormSet.form.base_fields['user'].queryset = User.objects.filter(is_active=True).order_by('last_name')
        formset = PaymentFormSet(queryset=Payment.objects.filter(pk__in=ids))

    setattr(formset, 'opts', {
        'verbose_name_plural': 'Payments',
        'model_name': 'Payment'
    })
    context = {
        'formset': formset,
        'change': False,
        'is_popup': False,
        'to_field': False,
        'save_on_top': False,
        'save_as': True,
        'show_save_and_continue': False,
        'has_delete_permission': False,
        'show_delete': False,
        'has_add_permission': True,
        'has_change_permission': True,
        'add': False
    }
    return TemplateResponse(request, template, context)

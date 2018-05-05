import datetime

from cartridge.shop import views as s_views
from cartridge.shop.forms import CartItemFormSet, DiscountForm
from cartridge.shop.models import Category, Order
from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.forms import modelformset_factory
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from mezzanine.conf import settings
from mezzanine.utils.views import paginate

from ffcsa.core.forms import CartDinnerForm, wrap_AddProductForm
from ffcsa.core.models import Payment
from .utils import ORDER_CUTOFF_DAY, get_ytd_order_total, get_ytd_payment_total, recalculate_remaining_budget


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

    return s_views.cart(request, template=template, cart_formset_class=cart_formset_class,
                        discount_form_class=discount_form_class, extra_context=extra_context)


def product(request, slug, template="shop/product.html", extra_context=None):
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
    response = s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)

    if isinstance(response, HttpResponseRedirect):
        request.method = 'GET'
        return s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)

    return response


@login_required
def order_history(request, template="shop/order_history.html"):
    ytd_order_total = get_ytd_order_total(request.user)
    ytd_payment_total = get_ytd_payment_total(request.user)

    extra_context = {
        'ytd_contrib': '{0:.2f}'.format(ytd_payment_total),
        'ytd_ordered': ytd_order_total,
        'budget': '{0:.2f}'.format(ytd_payment_total - ytd_order_total)
    }

    return s_views.order_history(request, template=template, extra_context=extra_context)


@login_required
def payment_history(request, template="ffcsa_core/payment_history.html"):
    """
    Display a list of the currently logged-in user's past orders.
    """
    all_payments = Payment.objects.filter(user__id=request.user.id)
    payments = paginate(all_payments.order_by('-date'),
                        request.GET.get("page", 1),
                        settings.SHOP_PER_PAGE_CATEGORY,
                        settings.MAX_PAGING_LINKS)
    context = {"payments": payments}
    return TemplateResponse(request, template, context)


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
        .filter(time__gte=order_date)

    attendees = [{'family': o.billing_detail_last_name, 'attending_dinner': o.attending_dinner}
                 for o in last_week_orders if o.attending_dinner > 0]

    context = {
        'attendees': attendees
    }

    return TemplateResponse(request, template, context)


User = get_user_model()


@staff_member_required
def admin_member_budgets(request, template="admin/member_budgets.html"):
    users = User.objects.filter(is_active=True)

    budgets = []

    for user in users:
        ytd_contrib = get_ytd_payment_total(user)
        ytd_ordered = get_ytd_order_total(user)
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


@csrf_protect
@staff_member_required
def admin_bulk_payments(request, template="admin/bulk_payments.html"):
    new_month = request.GET.get('newMonth', False)
    ids = request.GET.get('ids', [])
    if ids and isinstance(ids, str):
        ids = ids.split(',')

    if new_month:
        users = User.objects.filter(is_active=True)
        extra = users.count() + 1
        can_delete = True
    else:
        extra = 1 if len(ids) > 0 else 2
        can_delete = len(ids) > 0

    PaymentFormSet = modelformset_factory(Payment, fields=('user', 'date', 'amount'), can_delete=can_delete,
                                          extra=extra)

    if request.method == 'POST':
        formset = PaymentFormSet(request.POST)
        if formset.is_valid():
            formset.save()
            recalculate_remaining_budget(request)
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

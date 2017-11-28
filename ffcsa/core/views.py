import datetime
from functools import reduce

from cartridge.shop import views as s_views
from cartridge.shop.forms import AddProductForm, CartItemFormSet, DiscountForm
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

from ffcsa.core.forms import CartDinnerForm
from ffcsa.core.models import Payment
from .utils import get_ytd_orders, ORDER_CUTOFF_DAY


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


def product(request, slug, template="shop/product.html",
            form_class=AddProductForm, extra_context=None):
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

    response = s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)

    if isinstance(response, HttpResponseRedirect):
        request.method = 'GET'
        return s_views.product(request, slug, template=template, form_class=form_class, extra_context=extra_context)

    return response


@login_required
def order_history(request, template="shop/order_history.html"):
    today = datetime.date.today()

    ytd_orders = get_ytd_orders(request.user)

    ytd_sum = reduce(lambda x, y: x + y.total, ytd_orders, 0)

    month_orders = ytd_orders.filter(time__month=today.month)
    month_sum = reduce(lambda x, y: x + y.total, month_orders, 0)

    weekly_budget = request.user.profile.weekly_budget if request.user.profile.weekly_budget else Decimal(0)
    ytd_contrib = Decimal(request.user.profile.csa_months_ytd()) * weekly_budget * Decimal(4.3333)  # 4.333 wks/month

    extra_context = {
        'ytd_contrib': '{0:.2f}'.format(ytd_contrib),
        'ytd_ordered': ytd_sum,
        'month_contrib': '{0:.2f}'.format(weekly_budget * Decimal(4.3333)),
        'month_ordered': month_sum
    }

    return s_views.order_history(request, template=template, extra_context=extra_context)


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


@csrf_protect
@staff_member_required
def admin_bulk_payments(request, template="admin/bulk_payments.html"):
    new_month = request.GET.get('newMonth', False)
    ids = request.GET.get('ids', [])
    if ids and isinstance(ids, str):
        ids = ids.split(',')

    if new_month:
        User = get_user_model()
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
            return HttpResponseRedirect(reverse('admin:ffcsa_core_payment_changelist'))

    if new_month:
        formset = PaymentFormSet(queryset=Payment.objects.none())
        TWOPLACES = Decimal(10) ** -2

        i = 0
        for user in users:
            form = formset.forms[i]
            weekly_budget = user.profile.weekly_budget if user.profile.weekly_budget else Decimal(0)
            form.initial = {
                'amount': (weekly_budget * Decimal(4.3333)).quantize(TWOPLACES),  # 4.333 wks/month
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

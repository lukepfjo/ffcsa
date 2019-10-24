from ffcsa.core.budgets import clear_cached_budget
from cartridge.shop.utils import recalculate_remaining_budget


class BudgetMiddleware(object):
    """
    Verifies remaining_budget is in the current session
    """

    def process_response(self, request, response):
        # make sure that remaining_budget attached to the current session
        remaining_budget = request.session.get("remaining_budget", None)
        if hasattr(request, 'user') and request.user.is_authenticated() and remaining_budget is None:
            recalculate_remaining_budget(request)

        return response


class DiscountMiddleware(object):
    """
    Verifies discount_code is in the current session if the user has a discount_code

    This middleware should run before the BudgetMiddleware
    """

    def process_response(self, request, response):
        if request.session.get("discount_code", None):
            if not hasattr(request, 'user') \
                    or not request.user.is_authenticated() or not request.user.profile.discount_code:
                request.session["discount_code"] = None
                request.session["discount_total"] = None
                if hasattr(request, 'user'):
                    clear_cached_budget(request.user)

        elif hasattr(request, 'user') and request.user.is_authenticated() and request.user.profile.discount_code:
            request.session["discount_code"] = request.user.profile.discount_code.code
            total = request.cart.calculate_discount(
                request.user.profile.discount_code)
            request.session["discount_total"] = str(total)
            clear_cached_budget(request.user)

        return response

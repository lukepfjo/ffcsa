from ffcsa.core.budgets import recalculate_budget_for_user
from ffcsa.core.utils import recalculate_remaining_budget


class BudgetMiddleware(object):
    """
    Verifies remaining_budget is in the current session
    """

    def process_response(self, request, response):
        # make sure that remaining_budget attached to the current session
        remaining_budget = request.session.get("remaining_budget", None)
        if hasattr(request, 'user') and request.user.is_authenticated() and (
                remaining_budget is None or recalculate_budget_for_user(request.user)):
            recalculate_remaining_budget(request)

        return response

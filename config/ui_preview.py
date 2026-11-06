"""Allow narrowly scoped, same-origin UI previews; keep normal frame protection."""
from django.urls import reverse


PREVIEW_ROUTES = (
    'home', 'procurement:workflow', 'procurement:workflow_headcounts', 'inventory:ingredient_list',
    'meals:weekly_mealplan_create', 'procurement:workflow_ledger', 'meals:cooking_index',
)


class UIComparisonFrameMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (request.method == 'GET' and request.GET.get('snp_preview') == '1'
                and response.status_code == 200
                and request.user.is_authenticated
                and request.path in {reverse(name) for name in PREVIEW_ROUTES}):
            response['X-Frame-Options'] = 'SAMEORIGIN'
        return response

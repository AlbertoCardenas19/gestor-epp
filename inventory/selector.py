"""Small request picker, paginated across the same common availability as writes."""
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import TemplateView

from .common import common_items
from .views import ProjectMixin


def selector_context(params, selected_id=None):
    items = common_items()
    query = params.get('q', '').strip()[:500]
    if query:
        items = items.filter(Q(name__icontains=query) | Q(type_label__icontains=query))
    page = Paginator(items, 6).get_page(params.get('page', 1))
    # Selection is outside the results container; it survives pagination and search.
    selected = None
    if str(selected_id or '').isdigit() and len(str(selected_id)) <= 19 and int(selected_id) <= 9223372036854775807:
        selected = common_items().filter(pk=selected_id).first()
    return {'selector_page': page, 'selector_query': query, 'selected_item': selected}


class RequestItemSelectorView(ProjectMixin, TemplateView):
    template_name = 'inventory/item_choices.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(**selector_context(self.request.GET), **kwargs)

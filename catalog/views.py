from django.db.models import Case, CharField, Value, When
from django.views.generic import CreateView, DetailView, ListView

from .forms import ItemForm
from .models import Item
from projects.datatables import DataTableView
from django.template.loader import render_to_string


class ItemQuerysetMixin:
    def get_queryset(self):
        return Item.objects.annotate(type_label=Case(
            When(item_type=Item.Type.EPP, then=Value('EPP')),
            default=Value('Señalética'), output_field=CharField(),
        )).order_by('name', 'pk')


class ItemListView(ItemQuerysetMixin, ListView):
    model = Item
    template_name = 'catalog/list.html'
    context_object_name = 'items'
    paginate_by = 10


class ItemDataView(ItemQuerysetMixin, DataTableView):
    order_columns = ('name', 'type_label', 'description', None)
    search_fields = ('name', 'type_label', 'description')
    default_order = ('name', 'pk')

    def serialize_record(self, item):
        return {
            'name': item.name, 'type': item.get_item_type_display(), 'description': item.description or 'Sin descripción.',
            'actions': render_to_string('projects/row_actions.html', {
                'action_id': item.pk, 'action_label': item.name,
                'detail_url': item.get_absolute_url(), 'detail_label': 'Ver elemento',
            }),
        }


class ItemCreateView(CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'catalog/form.html'


class ItemDetailView(DetailView):
    model = Item
    template_name = 'catalog/detail.html'
    context_object_name = 'item'

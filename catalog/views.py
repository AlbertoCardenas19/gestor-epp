from django.db.models import Case, CharField, Value, When
from django.views.generic import CreateView, DetailView, RedirectView
from django.db import transaction
from django.utils import timezone
import uuid

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


class ItemListView(RedirectView):
    pattern_name = 'stock:list'
    query_string = True


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

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)
        quantity = form.cleaned_data.get('initial_quantity') or 0
        if quantity:
            from inventory.models import StockPosition, StockRecord
            from inventory.services import _create_record
            position = StockPosition.objects.create(project=None, item=self.object)
            _create_record(position, StockRecord.Operation.OPENING, {
                'quantity': quantity, 'occurred_on': form.cleaned_data.get('initial_date') or timezone.localdate(),
                'observation': '', 'submission_key': uuid.uuid4(),
            })
        return response


class ItemDetailView(DetailView):
    model = Item
    template_name = 'catalog/detail.html'
    context_object_name = 'item'

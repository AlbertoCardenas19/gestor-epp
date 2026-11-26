from django.views.generic import CreateView, DetailView, TemplateView, UpdateView
from django.db import transaction
from django.urls import reverse_lazy
from django.utils import timezone
import uuid

from .forms import CategoryForm, ItemCatalogForm, ItemForm
from .models import Category, Item
from projects.datatables import DataTableView
from django.template.loader import render_to_string


class ItemQuerysetMixin:
    def get_queryset(self):
        return Item.objects.with_category_label().order_by('name', 'pk')


class ItemListView(TemplateView):
    template_name = 'catalog/list.html'


class ItemDataView(ItemQuerysetMixin, DataTableView):
    order_columns = ('name', 'category_label', 'description', None)
    search_fields = ('name', 'category_label', 'description')
    default_order = ('name', 'pk')

    def serialize_record(self, item):
        return {
            'name': item.name, 'item_url': item.get_absolute_url(), 'type': item.category_label or 'Sin categorías', 'description': item.description or 'Sin descripción.',
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

    def get_context_data(self, **kwargs):
        from inventory.availability import available_quantity
        from inventory.common import item_projects
        return super().get_context_data(balance=available_quantity(self.object.pk),
            project_options=item_projects(self.object), movement_project=self.request.GET.get('project', ''), **kwargs)


class CategoryListView(TemplateView):
    template_name = 'catalog/category_list.html'


class CategoryDataView(DataTableView):
    order_columns = ('name',)
    search_fields = ('name',)
    default_order = ('name', 'pk')

    def get_queryset(self):
        return Category.objects.all()

    def serialize_record(self, category):
        return {'name': category.name}


class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'catalog/category_form.html'
    success_url = reverse_lazy('catalog:categories')


class ItemUpdateView(UpdateView):
    model = Item
    form_class = ItemCatalogForm
    template_name = 'catalog/form.html'

from django.views.generic import CreateView, DetailView, TemplateView, UpdateView
from django.db import transaction
from django.urls import reverse, reverse_lazy
from django.utils import timezone
import uuid

from .forms import CategoryForm, ItemCatalogForm, ItemForm
from .models import Category, Item
from projects.datatables import DataTableView


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
        from inventory.models import StockPosition
        from projects.models import Project
        actions = [
            {'label': 'Registrar entrada', 'url': reverse('stock:receive', args=[self.object.pk])},
            {'label': 'Solicitar para un proyecto', 'url': reverse('stock:request', args=[self.object.pk])},
            {'label': 'Editar elemento', 'url': reverse('catalog:update', args=[self.object.pk])},
        ]
        project_key = self.request.GET.get('project', '')
        scoped_project = Project.objects.filter(pk=int(project_key)).first() if project_key.isascii() and project_key.isdigit() and len(project_key) < 19 else None
        if scoped_project and not StockPosition.objects.filter(project=scoped_project, item=self.object).exists():
            actions.append({'label': 'Registrar apertura del proyecto',
                            'url': reverse('inventory:open', args=[scoped_project.pk, self.object.pk])})
        return super().get_context_data(balance=available_quantity(self.object.pk), info_actions=actions,
            action_key=f'item-{self.object.pk}', action_label=self.object.name, scoped_project=scoped_project, **kwargs)


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

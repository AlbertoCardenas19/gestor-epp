from django.db.models import Case, CharField, Value, When
from django.views.generic import CreateView, DetailView, ListView

from .forms import ItemForm
from .models import Item
from projects.tables import TableViewMixin


class ItemListView(TableViewMixin, ListView):
    model = Item
    template_name = 'catalog/list.html'
    context_object_name = 'items'
    search_fields = ('name', 'description', 'type_label')
    default_sort = 'name'
    sort_options = (
        ('name', 'Nombre: A–Z', ('name', 'pk')),
        ('-name', 'Nombre: Z–A', ('-name', '-pk')),
        ('type', 'Tipo: A–Z', ('type_label', 'name', 'pk')),
        ('-type', 'Tipo: Z–A', ('-type_label', 'name', 'pk')),
        ('-description', 'Descripción: Z–A', ('-description', '-pk')),
        ('description', 'Descripción: A–Z', ('description', 'pk')),
    )

    table_columns = (('Nombre', 'name', '-name'), ('Tipo', 'type', '-type'), ('Descripción', 'description', '-description'))

    def get_queryset(self):
        items = super().get_queryset().annotate(type_label=Case(
            When(item_type=Item.Type.EPP, then=Value('EPP')),
            default=Value('Señalética'), output_field=CharField(),
        ))
        return self.filter_table(items)


class ItemCreateView(CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'catalog/form.html'


class ItemDetailView(DetailView):
    model = Item
    template_name = 'catalog/detail.html'
    context_object_name = 'item'

from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView, DetailView, ListView

from .forms import ItemForm
from .models import Item


class ItemListView(ListView):
    model = Item
    template_name = 'catalog/list.html'
    context_object_name = 'items'


class ItemCreateView(SuccessMessageMixin, CreateView):
    model = Item
    form_class = ItemForm
    template_name = 'catalog/form.html'
    success_message = 'Elemento creado correctamente.'


class ItemDetailView(DetailView):
    model = Item
    template_name = 'catalog/detail.html'
    context_object_name = 'item'

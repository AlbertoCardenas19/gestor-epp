from django import forms
from django.utils import timezone

from .models import Category, Item


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        widgets = {'name': forms.TextInput(attrs={'class': 'form-control'})}
        error_messages = {'name': {
            'required': 'Escribe el nombre de la categoría.',
            'unique': 'Ya existe una categoría con ese nombre.',
        }}


class ItemCatalogForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'categories', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'categories': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 4}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        error_messages = {
            'name': {'required': 'Escribe el nombre del elemento.'},
            'categories': {'required': 'Selecciona al menos una categoría.'},
        }


class ItemForm(ItemCatalogForm):
    initial_quantity = forms.IntegerField(label='Stock inicial', min_value=0, max_value=9223372036854775807,
        required=False, initial=0, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}))
    initial_date = forms.DateField(label='Fecha del stock inicial', required=False, initial=timezone.localdate,
        widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if self.is_bound and name in self.errors:
                field.widget.attrs.update({
                    'class': f"{field.widget.attrs['class']} is-invalid",
                    'aria-invalid': 'true',
                    'aria-describedby': f'id_{name}_errors',
                })

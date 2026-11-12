from django import forms

from .models import Item


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['name', 'item_type', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'autofocus': True}),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
        error_messages = {
            'name': {'required': 'Escribe el nombre del elemento.'},
            'item_type': {
                'required': 'Selecciona el tipo de elemento.',
                'invalid_choice': 'Selecciona EPP o Señalética.',
            },
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['item_type'].choices = [('', 'Selecciona un tipo'), *Item.Type.choices]
        for name, field in self.fields.items():
            if self.is_bound and name in self.errors:
                field.widget.attrs.update({
                    'class': f"{field.widget.attrs['class']} is-invalid",
                    'aria-invalid': 'true',
                    'aria-describedby': f'id_{name}_errors',
                })

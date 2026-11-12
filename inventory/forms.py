import uuid

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import StockRecord


class StockForm(forms.Form):
    quantity = forms.IntegerField(label='Cantidad', min_value=0, max_value=9223372036854775807,
                                 widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}))
    occurred_on = forms.DateField(label='Fecha del conteo o recepción', input_formats=['%Y-%m-%d'],
                                  widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}))
    observation = forms.CharField(label='Observación', required=False,
                                  widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    submission_key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)

    def __init__(self, *args, operation, **kwargs):
        super().__init__(*args, **kwargs)
        if operation == StockRecord.Operation.RECEIPT:
            self.fields['quantity'].min_value = 1
            self.fields['quantity'].validators = [MinValueValidator(1), MaxValueValidator(9223372036854775807)]
            self.fields['quantity'].widget.attrs['min'] = 1
        if self.is_bound:
            for name in self.errors:
                if name in self.fields and not self.fields[name].widget.is_hidden:
                    self.fields[name].widget.attrs.update({
                        'class': 'form-control is-invalid', 'aria-invalid': 'true',
                        'aria-describedby': f'id_{name}_errors',
                    })


class CorrectionForm(StockForm):
    reason = forms.CharField(label='Motivo de la corrección',
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

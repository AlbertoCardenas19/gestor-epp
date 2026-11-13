import uuid

from django import forms
from django.core.validators import MaxValueValidator, MinValueValidator

from .models import StockRecord
from catalog.models import Item
from projects.models import Project


class InlineErrorsMixin:
    def add_error(self, field, error):
        super().add_error(field, error)
        for name in self._errors:
            if name in self.fields and not self.fields[name].widget.is_hidden:
                widget = self.fields[name].widget
                classes = widget.attrs.get('class', 'form-control').split()
                if 'is-invalid' not in classes:
                    classes.append('is-invalid')
                widget.attrs.update({'class': ' '.join(classes), 'aria-invalid': 'true',
                                     'aria-describedby': f'id_{name}_errors'})


class StockForm(InlineErrorsMixin, forms.Form):
    quantity = forms.IntegerField(label='Cantidad', min_value=0, max_value=9223372036854775807,
                                 widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}))
    occurred_on = forms.DateField(label='Fecha del conteo o recepción', input_formats=['%Y-%m-%d'],
                                  widget=forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}))
    observation = forms.CharField(label='Observación', required=False,
                                  widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    submission_key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)

    def __init__(self, *args, operation, **kwargs):
        super().__init__(*args, **kwargs)
        if operation in [StockRecord.Operation.RECEIPT, StockRecord.Operation.DELIVERY]:
            self.fields['quantity'].min_value = 1
            self.fields['quantity'].validators = [MinValueValidator(1), MaxValueValidator(9223372036854775807)]
            self.fields['quantity'].widget.attrs['min'] = 1
        if operation == StockRecord.Operation.DELIVERY:
            self.fields['occurred_on'].label = 'Fecha de entrega'



class CorrectionForm(StockForm):
    reason = forms.CharField(label='Motivo de la corrección',
                              widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))


class DeliveryForm(StockForm):
    worker_full_name = forms.CharField(
        label='Nombre completo del trabajador',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'off'}),
    )
    field_order = ['worker_full_name', 'quantity', 'occurred_on', 'observation', 'submission_key']


class DeliveryCorrectionForm(DeliveryForm):
    destination_project = forms.ModelChoiceField(
        label='Proyecto', queryset=Project.objects.all(), empty_label='Selecciona un proyecto',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    destination_item = forms.ModelChoiceField(
        label='Elemento', queryset=Item.objects.all(), empty_label='Selecciona un elemento',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    reason = forms.CharField(label='Motivo de la corrección',
                             widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    field_order = ['destination_project', 'destination_item', 'worker_full_name', 'quantity',
                   'occurred_on', 'observation', 'reason', 'submission_key']


class DeliveryCancellationForm(InlineErrorsMixin, forms.Form):
    reason = forms.CharField(
        label='Motivo de la anulación',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        error_messages={'required': 'Escribe el motivo de la anulación.'},
    )


class RequestDeliveryCorrectionForm(DeliveryForm):
    destination_request = forms.ModelChoiceField(label='Solicitud de destino', queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'}))
    reason = forms.CharField(label='Motivo de la corrección', widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    field_order = ['destination_request', 'worker_full_name', 'quantity', 'occurred_on', 'observation', 'reason', 'submission_key']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import StockRequest
        self.fields['destination_request'].queryset = StockRequest.objects.select_related('project', 'item').all()

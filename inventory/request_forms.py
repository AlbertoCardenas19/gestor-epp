import uuid

from django import forms

from catalog.models import Item
from .forms import InlineErrorsMixin


class RequestForm(InlineErrorsMixin, forms.Form):
    item = forms.ModelChoiceField(label='Elemento', queryset=Item.objects.order_by('name', 'pk'),
                                   widget=forms.HiddenInput())
    quantity = forms.IntegerField(label='Cantidad solicitada', min_value=1, max_value=9223372036854775807,
                                  widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'step': 1}))
    observation = forms.CharField(label='Observación', required=False,
                                   widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    submission_key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)


class RequestActionForm(InlineErrorsMixin, forms.Form):
    submission_key = forms.UUIDField(initial=uuid.uuid4, widget=forms.HiddenInput)


class RequestReductionForm(RequestActionForm):
    pending_quantity = forms.IntegerField(label='Cantidad pendiente que conservar', min_value=0, max_value=9223372036854775807,
        help_text='Indica cero para cancelar todo lo pendiente. Las entregas realizadas se conservan.',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': 1}))
    reason = forms.CharField(label='Motivo de la reducción o cancelación',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))

from django import forms
from django.forms import formset_factory
from django.urls import reverse

from catalog.forms import ItemCatalogForm
from catalog.models import Item
from projects.models import Project

from .models import Invoice, ReferencePrice, Supplier
from .services import HEADER


class StyledForm:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if widget.is_hidden or isinstance(widget, forms.CheckboxInput):
                continue
            widget.attrs.setdefault('class', 'form-select' if isinstance(widget, forms.Select) else 'form-control')


class SupplierForm(StyledForm, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ('name', 'rut', 'contact', 'phone', 'email')


def picker_field(queryset, label, *, required=True):
    return forms.ModelChoiceField(queryset=queryset, label=label, required=required, widget=forms.HiddenInput(attrs={'data-picker-value': ''}))


def date_input():
    return forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'})


class InvoiceForm(StyledForm, forms.ModelForm):
    supplier = picker_field(Supplier.objects.all(), 'Proveedor')
    reason = forms.CharField(label='Motivo de la corrección', widget=forms.Textarea(attrs={'rows': 2}))
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)

    class Meta:
        model = Invoice
        fields = HEADER
        widgets = {name: date_input() for name in ('issued_on', 'due_on', 'paid_on')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['revision'] = self.instance.revision
        else:
            del self.fields['reason'], self.fields['revision']

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('payment_status')
        if status == Invoice.Payment.PAID and not cleaned.get('paid_on'):
            self.add_error('paid_on', 'Indica la fecha de pago.')
        elif status == Invoice.Payment.PENDING and cleaned.get('paid_on'):
            self.add_error('paid_on', 'Deja la fecha de pago vacía si el pago está pendiente.')
        return cleaned


class InvoiceLineForm(StyledForm, forms.Form):
    item = picker_field(Item.objects.all(), 'Elemento', required=False)
    quantity = forms.IntegerField(label='Cantidad', min_value=1, max_value=2**63 - 1)
    unit_price = forms.IntegerField(label='Precio unitario sin IVA (CLP)', min_value=0, max_value=2**63 - 1)


class AllocationForm(StyledForm, forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.order_by('name', 'pk'), label='Proyecto')
    quantity = forms.IntegerField(label='Cantidad asignada', min_value=1, max_value=2**63 - 1)


InvoiceLines = formset_factory(InvoiceLineForm, min_num=1, validate_min=True, extra=0, can_delete=True)
Allocations = formset_factory(AllocationForm, extra=0, can_delete=True)


class ReferencePriceForm(StyledForm, forms.ModelForm):
    item = picker_field(Item.objects.all(), 'Elemento')

    class Meta:
        model = ReferencePrice
        fields = ('item', 'unit_price')


class ReceiptForm(forms.Form):
    revision = forms.IntegerField(widget=forms.HiddenInput, min_value=0)


class CancellationForm(StyledForm, ReceiptForm):
    reason = forms.CharField(label='Motivo de la anulación', widget=forms.Textarea(attrs={'rows': 3}))


class PaymentForm(StyledForm, ReceiptForm):
    paid_on = forms.DateField(label='Fecha de pago', widget=date_input())


class InvoiceLinesEditor:
    def __init__(self, data=None, invoice=None):
        existing = list(invoice.lines.prefetch_related('allocations')) if invoice else []
        self.formset = InvoiceLines(data, prefix='lines', initial=[
            {'item': line.item_id, 'quantity': line.quantity, 'unit_price': line.unit_price}
            for line in existing
        ])
        self.rows = [
            self.build_row(form, data, existing[index] if index < len(existing) else None)
            for index, form in enumerate(self.formset)
        ]
        self.empty_row = self.build_row(self.formset.empty_form)

    @staticmethod
    def build_row(form, data=None, line=None):
        if data is not None:
            form.empty_permitted = False
        allocations = Allocations(data, prefix=f'{form.prefix}-allocations', initial=[
            {'project': row.project_id, 'quantity': row.quantity} for row in line.allocations.all()
        ] if line else [])
        new_item = ItemCatalogForm(data, prefix=f'{form.prefix}-new')
        if data is not None and data.get(form.add_prefix('item')) and not new_item.has_changed():
            new_item = ItemCatalogForm(prefix=new_item.prefix)
        return {'form': form, 'allocations': allocations, 'new_item': new_item,
                'item_picker': selector('item', form['item'], form.initial.get('item'))}

    def clean(self):
        formset_valid = self.formset.is_valid()
        valid = formset_valid
        lines = []
        for row in self.rows:
            form, allocations, new_item = row['form'], row['allocations'], row['new_item']
            values = getattr(form, 'cleaned_data', {})
            if values.get('DELETE'):
                continue
            allocations_valid = allocations.is_valid()
            valid &= allocations_valid
            item = values.get('item')
            if item and new_item.has_changed():
                form.add_error('item', 'Selecciona un elemento existente o crea uno nuevo en esta línea.')
                valid = False
            elif not item and 'item' not in form.errors:
                valid &= new_item.is_valid()
            if form.errors or not values or not allocations_valid:
                valid = False
                continue
            lines.append({'item': item, 'new_item': new_item,
                          'quantity': values['quantity'], 'unit_price': values['unit_price'],
                          'allocations': [(entry['project'], entry['quantity']) for entry in allocations.cleaned_data
                                          if entry and not entry.get('DELETE')]})
        return lines if valid else None


def selector(kind, field, fallback=None):
    identifier = str(field.value() or fallback or '')
    selected = None
    if identifier.isascii() and identifier.isdigit() and len(identifier) <= 19 and int(identifier) < 2**63:
        selected = field.field.queryset.filter(pk=identifier).first()
    return {'field': field, 'selected': selected, 'source': reverse('purchases:choices', args=[kind]),
            'kind': kind}

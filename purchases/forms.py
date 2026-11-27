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
        widgets = {'issued_on': date_input()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['revision'] = self.instance.revision
        else:
            del self.fields['reason'], self.fields['revision']

class InvoiceLineForm(StyledForm, forms.Form):
    type = forms.ChoiceField(label='Tipo de línea', choices=(('item', 'Elemento'), ('service', 'Servicio')))
    item = picker_field(Item.objects.all(), 'Elemento', required=False)
    description = forms.CharField(label='Descripción del servicio', required=False, widget=forms.Textarea(attrs={'rows': 2}))
    quantity = forms.IntegerField(label='Cantidad', min_value=1, max_value=2**63 - 1)
    unit_price = forms.IntegerField(label='Precio unitario sin IVA (CLP)', min_value=0, max_value=2**63 - 1)


class AllocationForm(StyledForm, forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.order_by('name', 'pk'), label='Proyecto')
    quantity = forms.IntegerField(label='Cantidad asignada', min_value=1, max_value=2**63 - 1)


InvoiceLines = formset_factory(InvoiceLineForm, extra=0, can_delete=True)
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
    pass


class InvoiceLinesEditor:
    def __init__(self, data=None, invoice=None):
        existing = list(invoice.lines.prefetch_related('allocations')) if invoice else []
        self.formset = InvoiceLines(data, prefix='lines', initial=[
            {'type': 'item' if line.item_id else 'service', 'item': line.item_id,
             'description': line.description, 'quantity': line.quantity, 'unit_price': line.unit_price}
            for line in existing
        ])
        self.rows = [
            self.build_row(form, data, existing[index] if index < len(existing) else None)
            for index, form in enumerate(self.formset)
        ]
        self.empty_row = self.build_row(self.formset.empty_form)

    @staticmethod
    def build_row(form, data=None, line=None):
        if data is None and line is None:
            form.initial.setdefault('type', 'item')
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
            kind = values.get('type')
            if kind == 'service':
                if item or new_item.has_changed() or not values.get('description', '').strip():
                    form.add_error('description', 'Escribe una descripción de servicio y deja el elemento vacío.')
                    valid = False
                if any(entry and not entry.get('DELETE') for entry in allocations.cleaned_data):
                    form.add_error(None, 'Los servicios no se distribuyen entre proyectos.')
                    valid = False
            elif values.get('description', '').strip():
                form.add_error('description', 'La descripción de servicio corresponde solo a servicios.')
                valid = False
            if kind == 'item' and item and new_item.has_changed():
                form.add_error('item', 'Selecciona un elemento existente o crea uno nuevo en esta línea.')
                valid = False
            elif kind == 'item' and not item and 'item' not in form.errors:
                valid &= new_item.is_valid()
            if form.errors or not values or not allocations_valid:
                valid = False
                continue
            lines.append({'item': item if kind == 'item' else None, 'new_item': new_item if kind == 'item' else None,
                          'description': values.get('description', '').strip() if kind == 'service' else '',
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

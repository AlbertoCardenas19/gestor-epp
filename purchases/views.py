from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Case, Exists, OuterRef, Q, Value, When
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView, DetailView, TemplateView, UpdateView

from catalog.models import Item
from projects.datatables import DataTableView

from .forms import (CancellationForm, InvoiceForm, InvoiceLinesEditor, PaymentForm, ReceiptForm,
                    ReferencePriceForm, SupplierForm, selector)
from .models import Invoice, ReferencePrice, Supplier
from .services import cancel_invoice, mark_paid, receive_invoice, record_reference_price, save_invoice, save_invoice_lines


class SupplierList(TemplateView):
    template_name = 'purchases/supplier_list.html'


class SupplierData(DataTableView):
    order_columns = ('name', 'rut', 'contact', None)
    search_fields = ('name', 'rut', 'contact', 'phone', 'email')
    default_order = ('name', 'pk')

    def get_queryset(self):
        return Supplier.objects.all()

    def serialize_record(self, supplier):
        return {'name': supplier.name, 'rut': supplier.rut, 'contact': supplier.contact, 'url': supplier.get_absolute_url(),
                'actions': render_to_string('projects/row_actions.html', {
                    'action_id': supplier.pk, 'action_label': supplier.name, 'detail_url': supplier.get_absolute_url(),
                    'detail_label': 'Ver proveedor',
                })}


class SupplierCreate(CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'


class SupplierUpdate(UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'


class SupplierDetail(DetailView):
    model = Supplier
    context_object_name = 'supplier'
    template_name = 'purchases/supplier.html'

    def get_context_data(self, **kwargs):
        return super().get_context_data(info_actions=[
            {'label': 'Editar proveedor', 'url': reverse('purchases:supplier-edit', args=[self.object.pk])},
        ], action_key=f'supplier-{self.object.pk}', action_label=self.object.name, **kwargs)


class PriceData(DataTableView):
    order_columns = ('item__name', 'unit_price', 'recorded_at', None)
    search_fields = ('item__name',)
    default_order = ('-pk',)

    def get_queryset(self):
        supplier = get_object_or_404(Supplier, pk=self.kwargs['pk'])
        newer = ReferencePrice.objects.filter(supplier=supplier, item_id=OuterRef('item_id'), pk__gt=OuterRef('pk'))
        return ReferencePrice.objects.filter(supplier=supplier).select_related('item').annotate(has_newer=Exists(newer))

    def serialize_record(self, price):
        return {'item': price.item.name, 'url': price.item.get_absolute_url(), 'price': str(price.unit_price),
                'recorded': timezone.localtime(price.recorded_at).strftime('%d/%m/%Y %H:%M:%S'),
                'state': 'Histórico' if price.has_newer else 'Vigente'}


@require_http_methods(['GET', 'POST'])
def reference_price(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    form = ReferencePriceForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        record_reference_price(supplier, form.cleaned_data['item'], form.cleaned_data['unit_price'])
        return redirect(supplier)
    return render(request, 'purchases/price_form.html', {
        'supplier': supplier, 'form': form, 'picker': selector('item', form['item']),
    })


@require_http_methods(['GET'])
def choices(request, kind):
    query = request.GET.get('q', '').strip()[:500]
    if kind == 'item':
        results = Item.objects.with_category_label().order_by('name', 'pk')
        match = Q(name__icontains=query) | Q(category_label__icontains=query)
    elif kind == 'supplier':
        results = Supplier.objects.all()
        match = Q(name__icontains=query) | Q(rut__icontains=query)
    else:
        raise Http404
    page = Paginator(results.filter(match), 6).get_page(request.GET.get('page', 1))
    return render(request, 'inventory/item_choices.html', {'selector_page': page})


class InvoiceList(TemplateView):
    template_name = 'purchases/invoice_list.html'


class InvoiceData(DataTableView):
    order_columns = ('number', 'supplier__name', 'issued_on', 'calculated_total', 'payment_label', 'receipt_label', None)
    search_fields = ('number', 'supplier__name', 'supplier__rut', 'purchase_order', 'payment_method', 'payment_label', 'receipt_label')
    default_order = ('-issued_on', '-pk')

    def get_queryset(self):
        return Invoice.objects.select_related('supplier').annotate(
            payment_label=Case(When(payment_status=Invoice.Payment.PAID, then=Value('Pagada')), default=Value('Pendiente')),
            receipt_label=Case(When(cancelled_at__isnull=False, then=Value('Anulada')),
                               When(received_at__isnull=False, then=Value('Recibida')), default=Value('Por recibir')),
        )

    def serialize_record(self, invoice):
        return {'number': invoice.number, 'supplier': invoice.supplier.name, 'issued': invoice.issued_on.isoformat(),
                'total': str(invoice.calculated_total) if invoice.calculated_total is not None else 'Por completar',
                'payment': invoice.payment_label,
                'receipt': invoice.receipt_label, 'url': invoice.get_absolute_url(),
                'actions': render_to_string('projects/row_actions.html', {
                    'action_id': invoice.pk, 'action_label': invoice.number, 'detail_url': invoice.get_absolute_url(),
                    'detail_label': 'Ver factura',
                })}


class SupplierInvoiceData(InvoiceData):
    order_columns = ('number', 'issued_on', 'calculated_total', 'payment_label', 'receipt_label', None)
    search_fields = ('number', 'purchase_order', 'payment_method', 'payment_label', 'receipt_label')

    def get_queryset(self):
        get_object_or_404(Supplier, pk=self.kwargs['pk'])
        return super().get_queryset().filter(supplier_id=self.kwargs['pk'])


class InvoiceDetail(DetailView):
    model = Invoice
    context_object_name = 'invoice'
    template_name = 'purchases/invoice.html'

    def get_queryset(self):
        return Invoice.objects.select_related('supplier').prefetch_related(
            'lines__item', 'lines__allocations__project', 'events', 'movements__position__item', 'movements__replacement',
        )

    def get_context_data(self, **kwargs):
        invoice = self.object
        actions = []
        if not invoice.cancelled_at:
            if not invoice.received_at and invoice.lines.filter(item__isnull=False).exists():
                actions.append({'label': 'Confirmar recepción completa', 'url': reverse('purchases:receive', args=[invoice.pk])})
            if not invoice.received_at:
                actions.append({'label': 'Gestionar líneas', 'url': reverse('purchases:lines', args=[invoice.pk])})
            if invoice.payment_status == Invoice.Payment.PENDING:
                actions.append({'label': 'Marcar como pagada', 'url': reverse('purchases:pay', args=[invoice.pk])})
            actions.extend([
                {'label': 'Corregir', 'url': reverse('purchases:correct', args=[invoice.pk])},
                {'label': 'Anular', 'url': reverse('purchases:cancel', args=[invoice.pk]), 'danger': True},
            ])
        return super().get_context_data(info_actions=actions, action_key=f'invoice-{invoice.pk}',
            action_label=f'factura {invoice.number}', **kwargs)


@require_http_methods(['GET', 'POST'])
def invoice_edit(request, pk=None):
    invoice = get_object_or_404(Invoice, pk=pk) if pk is not None else None
    if invoice and invoice.cancelled_at:
        return redirect(invoice)
    data = request.POST if request.method == 'POST' else None
    form = InvoiceForm(data, instance=invoice)
    editor = InvoiceLinesEditor(data, invoice) if invoice else None
    if data is not None:
        header_valid = form.is_valid()
        lines = editor.clean() if editor else None
        if header_valid and (editor is None or lines is not None):
            try:
                saved = save_invoice(form.cleaned_data, lines, invoice_id=pk,
                                     reason=form.cleaned_data.get('reason', ''), revision=form.cleaned_data.get('revision'))
            except ValidationError as error:
                form.add_error(None, ValidationError(error.messages))
            else:
                return redirect(saved)
    return render(request, 'purchases/invoice_form.html', {
        'invoice': invoice, 'form': form, 'editor': editor,
        'supplier_picker': selector('supplier', form['supplier'], invoice.supplier_id if invoice else None),
    })


@require_http_methods(['GET', 'POST'])
def invoice_lines(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    if invoice.cancelled_at or invoice.received_at:
        return redirect(invoice)
    data = request.POST if request.method == 'POST' else None
    editor = InvoiceLinesEditor(data, invoice)
    errors = []
    if data is not None:
        lines = editor.clean()
        if lines is not None:
            try:
                save_invoice_lines(pk, lines, int(data.get('revision', '-1')))
            except (ValidationError, ValueError) as error:
                errors = error.messages if isinstance(error, ValidationError) else ['Revisión inválida.']
            else:
                return redirect(invoice)
    return render(request, 'purchases/invoice_lines.html', {
        'invoice': invoice, 'editor': editor, 'errors': errors,
    })


@require_http_methods(['GET', 'POST'])
def invoice_action(request, pk, action):
    invoice = get_object_or_404(Invoice, pk=pk)
    if action == 'receive' and (invoice.cancelled_at or invoice.received_at or not invoice.lines.filter(item__isnull=False).exists()):
        return redirect(invoice)
    if action == 'receive':
        title = 'Confirmar recepción completa'
        form_class = ReceiptForm
    elif action == 'cancel':
        title = 'Anular factura'
        form_class = CancellationForm
    else:
        title = 'Marcar factura como pagada'
        form_class = PaymentForm
    form = form_class(request.POST if request.method == 'POST' else None,
                      initial={'revision': invoice.revision})
    errors = []
    if request.method == 'POST' and form.is_valid():
        try:
            if action == 'receive':
                receive_invoice(pk, form.cleaned_data['revision'])
            elif action == 'cancel':
                cancel_invoice(pk, form.cleaned_data['reason'], form.cleaned_data['revision'])
            else:
                mark_paid(pk, form.cleaned_data['revision'])
        except ValidationError as error:
            errors = error.messages
        else:
            return redirect(invoice)
    return render(request, 'purchases/invoice_action.html', {
        'invoice': invoice, 'title': title, 'form': form, 'action': action, 'errors': errors,
    })

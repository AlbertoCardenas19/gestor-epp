from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from catalog.models import Category, Item
from inventory.availability import available_quantity
from inventory.models import StockRecord, StockRequest
from inventory.request_services import create_request, deliver_request
from inventory.services import correct_record
from projects.models import Project

from .models import Invoice, ReferencePrice, Supplier
from .services import cancel_invoice, mark_paid, receive_invoice, record_reference_price, save_invoice, save_invoice_lines

TODAY = date(2026, 11, 26)


def header(default_supplier, **changes):
    return {'supplier': default_supplier, 'number': '001', 'issued_on': TODAY,
            'payment_status': Invoice.Payment.PENDING, 'payment_method': '', 'purchase_order': '', **changes}


def line(item, quantity=20, unit_price=500, allocations=()):
    return {'item': item, 'description': '', 'quantity': quantity, 'unit_price': unit_price, 'allocations': allocations}


def service(description, quantity=1, unit_price=150):
    return {'item': None, 'description': description, 'quantity': quantity, 'unit_price': unit_price, 'allocations': ()}


class PurchaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.supplier = Supplier.objects.create(name='Seguridad SpA', rut='12.345.678-5')
        cls.other_supplier = Supplier.objects.create(name='Suministros Ltda.', rut='1-9')
        cls.item = Item.objects.create(name='Casco')
        cls.other_item = Item.objects.create(name='Botas')
        cls.north = Project.objects.create(name='Norte')
        cls.south = Project.objects.create(name='Sur')

    def payload(self, **changes):
        return {**header(self.supplier, supplier=self.supplier.pk),
                'lines-TOTAL_FORMS': 1, 'lines-INITIAL_FORMS': 0, 'lines-0-type': 'item', 'lines-0-item': self.item.pk,
                'lines-0-quantity': 20, 'lines-0-unit_price': 500,
                'lines-0-allocations-TOTAL_FORMS': 0, 'lines-0-allocations-INITIAL_FORMS': 0, **changes}

    def test_supplier_endpoints_and_search(self):
        response = self.client.post(reverse('purchases:supplier-create'), {'name': 'Nuevo', 'rut': '3-3'})
        supplier = Supplier.objects.get(name='Nuevo')
        self.assertRedirects(response, supplier.get_absolute_url())
        self.assertContains(self.client.get(supplier.get_absolute_url()), 'Sin registrar')
        response = self.client.post(reverse('purchases:supplier-edit', args=[supplier.pk]),
                                    {'name': supplier.name, 'rut': supplier.rut, 'contact': 'Ana'})
        self.assertRedirects(response, supplier.get_absolute_url())
        data = self.client.get(reverse('purchases:supplier-data'), {'search[value]': 'Ana'}).json()
        self.assertEqual(data['recordsFiltered'], 1)
        self.assertContains(self.client.get(reverse('purchases:choices', args=['supplier']), {'q': '3-3'}), 'Nuevo')

    def test_multiple_suppliers_reference_history_and_historical_purchase_price(self):
        first = record_reference_price(self.supplier, self.item, 400)
        second = record_reference_price(self.other_supplier, self.item, 600)
        invoice = save_invoice(header(self.supplier), [line(self.item)])
        third = record_reference_price(self.supplier, self.item, 450)
        self.assertEqual(list(ReferencePrice.objects.filter(item=self.item).values_list('pk', flat=True)),
                         [third.pk, second.pk, first.pk])
        result = self.client.get(reverse('purchases:price-data', args=[self.supplier.pk])).json()
        self.assertEqual([(row['price'], row['state']) for row in result['data']],
                         [('450', 'Vigente'), ('400', 'Histórico')])
        self.assertEqual(invoice.lines.get().unit_price, 500)
        self.assertEqual((invoice.net_total, invoice.vat_total, invoice.calculated_total), (10000, 1900, 11900))

    def test_invoice_number_is_unique_per_supplier_and_order_is_optional_or_shared(self):
        first = save_invoice(header(self.supplier), [line(self.item)])
        self.assertEqual(first.purchase_order, '')
        with self.assertRaises(ValidationError):
            save_invoice(header(self.supplier), [line(self.item)])
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invoice.objects.create(**header(self.supplier))
        save_invoice(header(self.other_supplier, purchase_order='OC-1'), [line(self.item)])
        save_invoice(header(self.other_supplier, number='002', purchase_order='OC-1'), [line(self.item)])
        self.assertEqual(Invoice.objects.filter(purchase_order='OC-1').count(), 2)

    def test_create_item_inline_and_distribute_with_unassigned_balance(self):
        category = Category.objects.get(name='Otros')
        payload = self.payload(**{'lines-0-item': '', 'lines-0-new-name': 'Linterna',
                                  'lines-0-new-categories': [category.pk],
                                  'lines-0-allocations-TOTAL_FORMS': 2,
                                  'lines-0-allocations-0-project': self.north.pk,
                                  'lines-0-allocations-0-quantity': 12,
                                  'lines-0-allocations-1-project': self.south.pk,
                                  'lines-0-allocations-1-quantity': 5})
        invoice = save_invoice(header(self.supplier))
        payload['revision'] = invoice.revision
        response = self.client.post(reverse('purchases:lines', args=[invoice.pk]), payload)
        self.assertRedirects(response, invoice.get_absolute_url())
        detail = invoice.lines.get()
        self.assertEqual(detail.item.name, 'Linterna')
        self.assertEqual(list(detail.item.categories.all()), [category])
        self.assertEqual(list(detail.allocations.values_list('quantity', flat=True)), [12, 5])
        self.assertEqual(detail.unassigned, 3)
        self.assertContains(self.client.get(invoice.get_absolute_url()), 'Sin asignar · 3')
        self.assertFalse(StockRecord.objects.exists())
        receive_invoice(invoice.pk)
        self.assertEqual(available_quantity(detail.item_id), 20)
        self.assertFalse(StockRequest.objects.exists())

    def test_excessive_distribution_rejected_without_saving_invoice_or_inline_item(self):
        invoice = save_invoice(header(self.supplier))
        response = self.client.post(reverse('purchases:lines', args=[invoice.pk]), self.payload(**{
            'revision': invoice.revision,
            'lines-0-item': '', 'lines-0-new-name': 'Linterna',
            'lines-0-new-categories': [Category.objects.get(name='Otros').pk],
            'lines-0-allocations-TOTAL_FORMS': 1, 'lines-0-allocations-0-project': self.north.pk,
            'lines-0-allocations-0-quantity': 21,
        }))
        self.assertContains(response, 'supera la cantidad de la línea')
        self.assertFalse(invoice.lines.exists())
        self.assertFalse(Item.objects.filter(name='Linterna').exists())

    def test_create_only_header_and_empty_invoice_blocks_receipt(self):
        response = self.client.post(reverse('purchases:create'), header(self.supplier, supplier=self.supplier.pk))
        invoice = Invoice.objects.get()
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertIsNone(invoice.calculated_total)
        self.assertContains(self.client.get(invoice.get_absolute_url()), 'Por completar')
        self.assertNotContains(self.client.get(invoice.get_absolute_url()), 'Confirmar recepción completa')
        with self.assertRaisesMessage(ValidationError, 'elemento'):
            receive_invoice(invoice.pk)

    def test_services_mixed_lines_rounding_and_payment_method(self):
        invoice = save_invoice(header(self.supplier, payment_method='Crédito'))
        self.assertEqual(invoice.payment_status, Invoice.Payment.PENDING)
        self.assertEqual(invoice.payment_method, 'Crédito')
        invoice = save_invoice_lines(invoice.pk, [service('Estampado')], invoice.revision)
        self.assertEqual((invoice.net_total, invoice.vat_total, invoice.calculated_total), (150, 29, 179))
        self.assertEqual(invoice.lines.get().item_id, None)
        self.assertFalse(StockRecord.objects.exists())
        self.assertNotContains(self.client.get(invoice.get_absolute_url()), 'Confirmar recepción completa')
        with self.assertRaisesMessage(ValidationError, 'elemento'):
            receive_invoice(invoice.pk)
        invoice = save_invoice_lines(invoice.pk, [line(self.item, 1, 127350), service('Estampado')], invoice.revision)
        self.assertEqual((invoice.net_total, invoice.vat_total, invoice.calculated_total), (127500, 24225, 151725))
        self.assertEqual(available_quantity(self.item.pk), 0)
        with self.assertRaisesMessage(ValidationError, 'cambió'):
            save_invoice_lines(invoice.pk, [service('Otro')], invoice.revision - 1)
        paid = mark_paid(invoice.pk, invoice.revision)
        self.assertEqual(paid.payment_status, Invoice.Payment.PAID)
        self.assertIsNone(paid.paid_on)
        self.assertEqual(paid.payment_method, 'Crédito')
        self.assertEqual(available_quantity(self.item.pk), 0)
        received = receive_invoice(invoice.pk, paid.revision)
        self.assertEqual((received.movements.count(), available_quantity(self.item.pk)), (1, 1))
        self.assertEqual(receive_invoice(invoice.pk).movements.count(), 1)
        with self.assertRaisesMessage(ValidationError, 'solo pueden modificarse'):
            save_invoice_lines(invoice.pk, [service('Otro')], received.revision)
        self.assertEqual(received.lines.count(), 2)

    def test_line_editor_accepts_service_without_catalog_item(self):
        invoice = save_invoice(header(self.supplier))
        response = self.client.post(reverse('purchases:lines', args=[invoice.pk]), {
            'revision': invoice.revision, 'lines-TOTAL_FORMS': 1, 'lines-INITIAL_FORMS': 0,
            'lines-0-type': 'service', 'lines-0-description': 'Servicio de estampado',
            'lines-0-quantity': 1, 'lines-0-unit_price': 150,
            'lines-0-allocations-TOTAL_FORMS': 0, 'lines-0-allocations-INITIAL_FORMS': 0,
        })
        self.assertRedirects(response, invoice.get_absolute_url())
        invoice.refresh_from_db()
        self.assertEqual(invoice.calculated_total, 179)
        self.assertContains(self.client.get(invoice.get_absolute_url()), 'Servicio de estampado')
        self.assertFalse(StockRecord.objects.exists())

    def test_payment_and_receipt_are_independent_and_retry_is_idempotent(self):
        invoice = save_invoice(header(self.supplier), [line(self.item, 12), line(self.item, 8)])
        self.assertFalse(StockRecord.objects.exists())
        self.assertRedirects(self.client.post(reverse('purchases:pay', args=[invoice.pk]),
                                             {'revision': invoice.revision}), invoice.get_absolute_url())
        invoice.refresh_from_db()
        self.assertEqual(invoice.payment_status, Invoice.Payment.PAID)
        self.assertIsNone(invoice.received_at)
        self.assertEqual(available_quantity(self.item.pk), 0)
        url = reverse('purchases:receive', args=[invoice.pk])
        for _ in range(2):
            self.assertRedirects(self.client.post(url, {'revision': invoice.revision}), invoice.get_absolute_url())
        movement = invoice.movements.get()
        self.assertIsNone(movement.position.project_id)
        self.assertEqual(movement.quantity, 20)
        self.assertEqual(available_quantity(self.item.pk), 20)
        self.assertContains(self.client.get(movement.get_absolute_url()), 'Ver factura de compra')
        with self.assertRaisesMessage(ValidationError, 'desde su factura'):
            correct_record(None, movement.pk, {})

    def test_receiving_pending_invoice_does_not_change_payment(self):
        invoice = save_invoice(header(self.supplier), [line(self.item)])
        invoice = receive_invoice(invoice.pk)
        self.assertEqual(invoice.payment_status, Invoice.Payment.PENDING)
        self.assertIsNone(invoice.paid_on)

    def test_correction_and_cancellation_before_receipt_leave_stock_untouched(self):
        invoice = save_invoice(header(self.supplier), [line(self.item)])
        revised = save_invoice(header(self.supplier, purchase_order='OC-A'), [line(self.other_item)],
                               invoice_id=invoice.pk, reason='Corregir documento', revision=invoice.revision)
        cancel_invoice(revised.pk, 'Duplicado', revised.revision)
        cancel_invoice(revised.pk, 'Duplicado', revised.revision)
        self.assertFalse(StockRecord.objects.exists())
        self.assertEqual(invoice.events.count(), 2)
        self.assertEqual(invoice.events.get(action='correct').before['lines'][0]['item_id'], self.item.pk)
        with self.assertRaisesMessage(ValidationError, 'anulada'):
            receive_invoice(invoice.pk)

    def test_correction_of_received_invoice_preserves_history_and_adjusts_changed_items_only(self):
        invoice = save_invoice(header(self.supplier), [line(self.item, 20, allocations=[(self.north, 12)])])
        invoice = receive_invoice(invoice.pk)
        movement = invoice.movements.get()
        payload = self.payload(**{
            'revision': invoice.revision, 'reason': 'Corregir precio', 'lines-INITIAL_FORMS': 1,
            'lines-0-unit_price': 550, 'lines-0-allocations-TOTAL_FORMS': 1,
            'lines-0-allocations-INITIAL_FORMS': 1, 'lines-0-allocations-0-project': self.north.pk,
            'lines-0-allocations-0-quantity': 12,
        })
        response = self.client.post(reverse('purchases:correct', args=[invoice.pk]), payload)
        self.assertRedirects(response, invoice.get_absolute_url())
        self.assertEqual(list(invoice.movements.values_list('pk', flat=True)), [movement.pk])
        invoice.refresh_from_db()
        with self.assertRaises(ValidationError):
            save_invoice(header(self.supplier), [line(self.item, 11, allocations=[(self.north, 12)])],
                         invoice_id=invoice.pk, reason='Cantidad', revision=invoice.revision)
        revised = save_invoice(header(self.supplier), [line(self.item, 12), line(self.other_item, 3)],
                               invoice_id=invoice.pk, reason='Cantidad', revision=invoice.revision)
        movement.refresh_from_db()
        self.assertEqual(movement.replacement.quantity, 12)
        self.assertEqual(available_quantity(self.item.pk), 12)
        self.assertEqual(available_quantity(self.other_item.pk), 3)
        self.assertEqual(invoice.events.order_by('pk').first().before['lines'][0]['unit_price'], 500)
        cancel_invoice(revised.pk, 'Factura errónea', revised.revision)
        cancel_invoice(revised.pk, 'Factura errónea', revised.revision)
        self.assertEqual(invoice.movements.count(), 3)
        self.assertFalse(invoice.movements.filter(voided_at__isnull=True).exists())
        self.assertEqual(available_quantity(self.item.pk), 0)
        self.assertEqual(available_quantity(self.other_item.pk), 0)

    def test_stock_already_committed_or_delivered_blocks_adjustment_and_rolls_back(self):
        invoice = receive_invoice(save_invoice(header(self.supplier), [line(self.other_item, 10), line(self.item, 20)]).pk)
        request = create_request(self.north, self.item,
                                 {'quantity': 5, 'observation': '', 'submission_key': uuid4()})
        for delivered in (False, True):
            if delivered:
                deliver_request(request, {'quantity': 5, 'observation': '', 'submission_key': uuid4(),
                                          'occurred_on': TODAY, 'worker_full_name': 'Ana Soto'})
            with self.assertRaisesMessage(ValidationError, 'stock insuficiente'):
                save_invoice(header(self.supplier), [line(self.item, 4)],
                             invoice_id=invoice.pk, reason='Error', revision=invoice.revision)
            with self.assertRaisesMessage(ValidationError, 'stock insuficiente'):
                cancel_invoice(invoice.pk, 'Error', invoice.revision)
            invoice.refresh_from_db()
            self.assertEqual(invoice.calculated_total, 17850)
            self.assertIsNone(invoice.cancelled_at)
            self.assertFalse(invoice.events.exists())
            self.assertEqual(invoice.lines.count(), 2)
            self.assertEqual(invoice.movements.filter(voided_at__isnull=True).count(), 2)
            self.assertEqual(available_quantity(self.item.pk), 15)
            self.assertEqual(available_quantity(self.other_item.pk), 10)

    def test_receipt_partial_write_rolls_back(self):
        invoice = save_invoice(header(self.supplier), [line(self.item), line(self.other_item)])
        from inventory.common import receive_common_stock
        with patch('purchases.services.receive_common_stock') as receive:
            def fail_second(item, data):
                if receive.call_count == 1:
                    return receive_common_stock(item, data)
                raise ValidationError('fallo de la segunda línea')
            receive.side_effect = fail_second
            with self.assertRaisesMessage(ValidationError, 'segunda línea'):
                receive_invoice(invoice.pk)
            self.assertEqual(receive.call_count, 2)
        invoice.refresh_from_db()
        self.assertIsNone(invoice.received_at)
        self.assertFalse(StockRecord.objects.exists())
        self.assertEqual(available_quantity(self.item.pk), 0)


class ConcurrentPurchaseTests(TransactionTestCase):
    def test_line_edit_and_receipt_recheck_revision_under_lock(self):
        supplier = Supplier.objects.create(name='Proveedor concurrente', rut='2-7')
        item = Item.objects.create(name='Casco concurrente')
        invoice = save_invoice(header(supplier), [line(item, 2)])
        barrier = Barrier(2)

        def run(operation):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return operation()
                except ValidationError:
                    return None
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(run, [
                lambda: save_invoice_lines(invoice.pk, [line(item, 3)], 0),
                lambda: receive_invoice(invoice.pk, 0),
            ]))
        self.assertEqual(sum(result is not None for result in results), 1)
        invoice.refresh_from_db()
        if invoice.received_at:
            self.assertEqual((invoice.lines.get().quantity, available_quantity(item.pk)), (2, 2))
        else:
            self.assertEqual((invoice.lines.get().quantity, available_quantity(item.pk)), (3, 0))

    def test_simultaneous_receipt_and_cancellation_do_not_duplicate_inventory_changes(self):
        supplier = Supplier.objects.create(name='Proveedor', rut='1-9')
        item = Item.objects.create(name='Elemento')
        invoice = save_invoice(header(supplier), [line(item)])
        self.run_twice(lambda: receive_invoice(invoice.pk, 0))
        invoice.refresh_from_db()
        self.assertEqual(invoice.movements.count(), 1)
        self.assertEqual(available_quantity(item.pk), 20)
        self.run_twice(lambda: cancel_invoice(invoice.pk, 'Error', invoice.revision))
        self.assertEqual(invoice.events.count(), 1)
        self.assertEqual(invoice.movements.count(), 1)
        self.assertEqual(available_quantity(item.pk), 0)

    def run_twice(self, action):
        barrier = Barrier(2)

        def run(_):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                action()
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(run, range(2)))


class InvoiceMigrationTests(TransactionTestCase):
    def test_historical_totals_and_stock_survive_migration(self):
        current = MigrationExecutor(connection).loader.graph.leaf_nodes()
        old = [('purchases', '0001_initial')]
        MigrationExecutor(connection).migrate(old)
        try:
            apps = MigrationExecutor(connection).loader.project_state(old).apps
            SupplierOld = apps.get_model('purchases', 'Supplier')
            InvoiceOld = apps.get_model('purchases', 'Invoice')
            InvoiceLineOld = apps.get_model('purchases', 'InvoiceLine')
            ItemOld = apps.get_model('catalog', 'Item')
            supplier = SupplierOld.objects.create(name='Histórico', rut='1-9')
            item = ItemOld.objects.create(name='Casco histórico')
            first = InvoiceOld.objects.create(supplier=supplier, number='H-1', issued_on=TODAY,
                                              due_on=TODAY, total=151725, payment_status='pending')
            InvoiceLineOld.objects.create(invoice=first, item=item, quantity=1, unit_price=127500)
            second = InvoiceOld.objects.create(supplier=supplier, number='H-2', issued_on=TODAY,
                                               due_on=TODAY, total=999, payment_status='paid', paid_on=TODAY)
            InvoiceLineOld.objects.create(invoice=second, item=item, quantity=1, unit_price=150)
            before_stock = StockRecord.objects.count()
            MigrationExecutor(connection).migrate(current)
            matching = Invoice.objects.get(pk=first.pk)
            differing = Invoice.objects.get(pk=second.pk)
            self.assertEqual((matching.transcribed_total, matching.calculated_total), (151725, 151725))
            self.assertFalse(matching.needs_reconciliation)
            self.assertEqual((differing.transcribed_total, differing.calculated_total), (999, 179))
            self.assertTrue(differing.needs_reconciliation)
            self.assertEqual((differing.due_on, differing.paid_on, differing.payment_status),
                             (TODAY, TODAY, Invoice.Payment.PAID))
            self.assertEqual(StockRecord.objects.count(), before_stock)
        finally:
            MigrationExecutor(connection).migrate(current)

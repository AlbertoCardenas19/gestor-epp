import uuid
from datetime import date

from django.test import TestCase
from django.urls import reverse

from catalog.models import Item
from projects.models import Project
from purchases.models import Invoice, Supplier
from .common import receive_common_stock
from .models import StockRequest
from .request_services import create_request


class UnifiedNavigationTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Proyecto Norte')
        self.other = Project.objects.create(name='Proyecto Sur')
        self.item = Item.objects.create(name='Casco')
        self.supplier = Supplier.objects.create(name='Proveedor', rut='12.345.678-9')
        self.invoice = Invoice.objects.create(supplier=self.supplier, number='F-15', issued_on=date(2026, 11, 27))

    def payload(self, quantity, **extra):
        return {'quantity': quantity, 'observation': '', 'submission_key': uuid.uuid4(), **extra}

    def test_tabs_and_supplier_invoice_scope(self):
        Invoice.objects.create(supplier=self.supplier, number='F-14', issued_on=date(2026, 11, 20))
        other_supplier = Supplier.objects.create(name='Otro', rut='1-9')
        Invoice.objects.create(supplier=other_supplier, number='AJENA', issued_on=date(2026, 11, 19))
        self.assertContains(self.client.get(self.invoice.get_absolute_url()), 'Detalles de compra')
        self.assertContains(self.client.get(self.supplier.get_absolute_url()), 'Elementos y precios')
        data = self.client.get(reverse('purchases:supplier-invoices-data', args=[self.supplier.pk])).json()
        self.assertEqual(data['data'][0]['number'], 'F-15')
        self.assertEqual(data['recordsTotal'], 2)
        ordered = self.client.get(reverse('purchases:supplier-invoices-data', args=[self.supplier.pk]),
            {'order[0][column]': 1, 'order[0][dir]': 'asc'}).json()
        self.assertEqual([row['number'] for row in ordered['data']], ['F-14', 'F-15'])
        searched = self.client.get(reverse('purchases:supplier-invoices-data', args=[self.supplier.pk]),
            {'search[value]': 'F-14'}).json()
        self.assertEqual(searched['recordsFiltered'], 1)
        self.assertEqual(self.client.get(reverse('purchases:supplier-invoices-data', args=[99999])).status_code, 404)

    def test_old_item_urls_redirect_to_one_ficha_with_project_scope(self):
        self.assertRedirects(self.client.get(reverse('stock:history', args=[self.item.pk])),
                             self.item.get_absolute_url() + '?tab=history', fetch_redirect_response=False)
        self.assertRedirects(self.client.get(reverse('inventory:history', args=[self.project.pk, self.item.pk])),
                             self.item.get_absolute_url() + f'?tab=history&project={self.project.pk}', fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse('inventory:history', args=[99999, self.item.pk])).status_code, 404)

    def test_request_from_item_reuses_service_and_has_correct_cancel(self):
        url = reverse('stock:request', args=[self.item.pk])
        self.assertContains(self.client.get(url), self.item.get_absolute_url())
        response = self.client.post(url, self.payload(3, item=self.item.pk, project=self.project.pk))
        self.assertRedirects(response, reverse('requests:list', args=[self.project.pk]))
        request = StockRequest.objects.get()
        self.assertEqual((request.project_id, request.item_id, request.purchase_quantity),
                         (self.project.pk, self.item.pk, 3))

    def test_manual_reservation_edit_and_delivery_keep_history(self):
        request = create_request(self.project, self.item, self.payload(5))
        receive_common_stock(self.item, self.payload(3, occurred_on=date(2026, 11, 27)))
        request.refresh_from_db()
        self.assertEqual(request.purchase_quantity, 5)
        edit = reverse('requests:edit', args=[self.project.pk, request.pk]) + '?modal=1'
        response = self.client.post(edit, self.payload(0, pending_quantity=5, reserve_quantity=3))
        self.assertEqual(response.json(), {'ok': True})
        request.refresh_from_db()
        self.assertEqual((request.purchase_quantity, request.reserved_quantity), (2, 3))
        delivery = reverse('requests:deliver', args=[self.project.pk, request.pk]) + '?modal=1'
        response = self.client.post(delivery, self.payload(2, occurred_on='2026-11-27', worker_full_name='Ana Pérez'))
        self.assertEqual(response.json(), {'ok': True})
        request.refresh_from_db()
        self.assertEqual((request.delivered_quantity, request.reserved_quantity, request.purchase_quantity), (2, 1, 2))
        history = self.client.get(request.get_absolute_url() + '?modal=1')
        self.assertContains(history, 'Ana Pérez')
        self.assertContains(history, 'Reserva ampliada')
        self.assertRedirects(self.client.get(request.get_absolute_url()), reverse('requests:list', args=[self.project.pk]))

    def test_edit_replay_is_idempotent_and_rejects_changed_payload(self):
        request = create_request(self.project, self.item, self.payload(5))
        receive_common_stock(self.item, self.payload(3, occurred_on=date(2026, 11, 27)))
        url = reverse('requests:edit', args=[self.project.pk, request.pk]) + '?modal=1'
        payload = self.payload(0, pending_quantity=5, reserve_quantity=3)
        for _ in range(2):
            self.assertEqual(self.client.post(url, payload).json(), {'ok': True})
        request.refresh_from_db()
        self.assertEqual(request.allocated_quantity, 3)
        response = self.client.post(url, {**payload, 'pending_quantity': 4, 'reason': 'Cambio'})
        self.assertContains(response, 'Este formulario ya se utilizó')
        request.refresh_from_db()
        self.assertEqual(request.cancelled_quantity, 0)

    def test_received_stock_can_be_split_between_selected_requests(self):
        first = create_request(self.project, self.item, self.payload(5))
        second = create_request(self.other, self.item, self.payload(5))
        receive_common_stock(self.item, self.payload(4, occurred_on=date(2026, 11, 27)))
        self.assertEqual(self.client.post(reverse('requests:edit', args=[self.project.pk, first.pk]) + '?modal=1',
            self.payload(0, pending_quantity=5, reserve_quantity=2)).json(), {'ok': True})
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((first.purchase_quantity, second.purchase_quantity), (3, 5))
        self.assertEqual(self.client.post(reverse('requests:edit', args=[self.other.pk, second.pk]) + '?modal=1',
            self.payload(0, pending_quantity=5, reserve_quantity=2)).json(), {'ok': True})
        second.refresh_from_db()
        self.assertEqual(second.purchase_quantity, 3)

    def test_edit_reduction_requires_reason_and_preserves_delivered(self):
        receive_common_stock(self.item, self.payload(5, occurred_on=date(2026, 11, 27)))
        request = create_request(self.project, self.item, self.payload(5))
        url = reverse('requests:edit', args=[self.project.pk, request.pk]) + '?modal=1'
        response = self.client.post(url, self.payload(0, pending_quantity=3, reserve_quantity=0))
        self.assertContains(response, 'Escribe el motivo')
        request.refresh_from_db()
        self.assertEqual(request.cancelled_quantity, 0)
        response = self.client.post(url, self.payload(0, pending_quantity=3, reserve_quantity=0,
            reason='Ya no se necesitan'))
        self.assertEqual(response.json(), {'ok': True})
        request.refresh_from_db()
        self.assertEqual((request.cancelled_quantity, request.pending_quantity), (2, 3))

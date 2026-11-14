import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase, Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from catalog.models import Item
from projects.models import Project
from .availability import available_quantity, reserved_quantity
from .common import receive_common_stock
from .models import StockPosition, StockRecord, StockRequest, StockRequestEvent
from .request_services import create_request, deliver_request, reduce_request, reserve_more
from .services import cancel_delivery, correct_record, deliver_stock, open_stock


def data(quantity=5, **extra):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **extra}


class RequestFlowTests(TestCase):
    def setUp(self):
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        self.other_item = Item.objects.create(name='Guantes', item_type=Item.Type.EPP)
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        self.opening = receive_common_stock(self.item, data(2))

    def request(self, quantity=5, project=None, item=None, **extra):
        return create_request(project or self.north, item or self.item, data(quantity, **extra))

    def counts(self):
        row = self.client.get(reverse('stock:data'), {'search[value]': 'Casco'}).json()['data'][0]
        return row['quantity'], row['delivered']

    def test_partial_reservation_and_uncovered_purchase_need(self):
        request = self.request()
        self.assertEqual((request.allocated_quantity, request.purchase_quantity, request.reserved_quantity), (2, 3, 2))
        self.assertEqual(StockPosition.common_balance(self.item.pk), 2)
        self.assertEqual(available_quantity(self.item.pk), 0)
        self.assertEqual(self.counts(), ('0', '0'))
        other = self.request(4, project=self.south)
        self.assertEqual((other.allocated_quantity, other.purchase_quantity), (0, 4))
        self.assertEqual(StockRequest.objects.count(), 2)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_no_stock_creates_only_a_purchase_need_and_never_negative_stock(self):
        request = self.request(item=self.other_item)
        self.assertEqual((request.allocated_quantity, request.purchase_quantity), (0, 5))
        self.assertEqual(request.state_label, 'En proceso')
        self.assertEqual(available_quantity(self.other_item.pk), 0)

    def test_confirmation_moves_reserved_to_real_delivery_without_double_deduction(self):
        request = self.request()
        payload = data(1, worker_full_name='Ana Pérez')
        record = deliver_request(request, payload)
        self.assertEqual(deliver_request(request, payload).pk, record.pk)
        request.refresh_from_db()
        self.assertEqual((request.delivered_quantity, request.reserved_quantity, request.purchase_quantity), (1, 1, 3))
        self.assertEqual(StockPosition.common_balance(self.item.pk), 1)
        self.assertEqual(self.counts(), ('0', '1'))
        self.assertEqual(record.stock_request_id, request.pk)
        self.assertEqual(StockRecord.objects.filter(operation='delivery').count(), 1)
        with self.assertRaises(ValidationError):
            deliver_request(request, data(2, worker_full_name='Luis Soto'))
        self.assertEqual(request.delivered_quantity, 1)

    def test_arrivals_do_not_auto_allocate_and_manual_reservation_retries_are_idempotent(self):
        request = self.request()
        receive_common_stock(self.item, data(4))
        request.refresh_from_db()
        self.assertEqual(request.allocated_quantity, 2)
        payload = data()
        reserve_more(request, payload)
        reserve_more(request, payload)
        request.refresh_from_db()
        self.assertEqual((request.allocated_quantity, request.purchase_quantity), (5, 0))
        self.assertEqual(self.counts(), ('1', '0'))
        self.assertEqual(request.events.filter(action='reserved').count(), 1)

    def test_reduce_purchase_need_before_releasing_reservations_and_cancel_with_reason(self):
        request = self.request()
        payload = data(pending_quantity=3, reason='Ahora se necesitan menos')
        reduce_request(request, payload)
        reduce_request(request, payload)
        request.refresh_from_db()
        self.assertEqual((request.quantity, request.cancelled_quantity, request.allocated_quantity, request.purchase_quantity), (5, 2, 2, 1))
        self.assertEqual(self.counts(), ('0', '0'))
        reduce_request(request, data(pending_quantity=1, reason='Reducir otra vez'))
        request.refresh_from_db()
        self.assertEqual((request.allocated_quantity, request.purchase_quantity), (1, 0))
        self.assertEqual(self.counts(), ('1', '0'))
        reduce_request(request, data(pending_quantity=0, reason='Cancelar pendiente'))
        request.refresh_from_db()
        self.assertEqual(request.state_label, 'Cancelado')
        self.assertEqual(self.counts(), ('2', '0'))
        self.assertEqual(request.events.count(), 4)

    def test_reduce_preserves_real_deliveries_and_rejects_empty_reason(self):
        request = self.request()
        record = deliver_request(request, data(1, worker_full_name='Ana Pérez'))
        with self.assertRaises(ValidationError):
            reduce_request(request, data(pending_quantity=0, reason=' '))
        reduce_request(request, data(pending_quantity=0, reason='Cancelar lo pendiente'))
        request.refresh_from_db();record.refresh_from_db()
        self.assertEqual((request.allocated_quantity, request.cancelled_quantity, request.delivered_quantity), (1, 4, 1))
        self.assertIsNone(record.voided_at)
        self.assertEqual(self.counts(), ('1', '1'))

    def test_cancel_requested_delivery_reinstates_same_reservation_once(self):
        request = self.request()
        record = deliver_request(request, data(2, worker_full_name='Ana Pérez'))
        original_data = (record.quantity, record.worker_full_name, record.occurred_on)
        _, changed = cancel_delivery(self.north, record.pk, 'Entrega equivocada')
        self.assertTrue(changed)
        record.refresh_from_db();timestamp=record.voided_at
        _, changed = cancel_delivery(self.north, record.pk, 'Reintento')
        self.assertFalse(changed)
        record.refresh_from_db()
        self.assertEqual(record.voided_at, timestamp)
        self.assertEqual(record.void_reason, 'Entrega equivocada')
        self.assertEqual((record.quantity, record.worker_full_name, record.occurred_on), original_data)
        self.assertEqual(request.reserved_quantity, 2)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 2)
        self.assertEqual(self.counts(), ('0', '0'))

    def test_correction_reinstates_difference_and_preserves_original(self):
        request = self.request()
        record = deliver_request(request, data(2, worker_full_name='Ana Pérez'))
        payload = data(1, worker_full_name='Luis Soto', destination_request=request, reason='Cantidad y destinatario equivocados')
        replacement = correct_record(self.north, record.pk, payload)
        self.assertEqual(correct_record(self.north, record.pk, payload).pk, replacement.pk)
        self.assertEqual((request.delivered_quantity, request.reserved_quantity), (1, 1))
        self.assertEqual(self.counts(), ('0', '1'))
        record.refresh_from_db()
        self.assertEqual(record.worker_full_name, 'Ana Pérez')
        self.assertEqual(record.quantity, 2)
        self.assertEqual(replacement.replaces_id, record.pk)
        with self.assertRaises(ValidationError):
            cancel_delivery(self.north, record.pk, 'No se puede anular un sustituido')
        self.assertIsNotNone(record.voided_at)

    def test_cross_request_correction_checks_pending_and_rolls_back_when_insufficient(self):
        receive_common_stock(self.other_item, data(3))
        source = self.request(2)
        destination = self.request(3, project=self.south, item=self.other_item)
        original = deliver_request(source, data(2, worker_full_name='Ana Pérez'))
        with self.assertRaises(ValidationError):
            correct_record(self.north, original.pk, data(4, destination_request=destination, worker_full_name='Ana Pérez', reason='Error'))
        original.refresh_from_db()
        self.assertIsNone(original.voided_at)
        self.assertEqual(source.delivered_quantity, 2)
        replacement = correct_record(self.north, original.pk, data(2, destination_request=destination, worker_full_name='Ana Pérez', reason='Otro proyecto y elemento'))
        self.assertEqual((source.reserved_quantity, destination.reserved_quantity), (2, 1))
        self.assertEqual(replacement.position.item_id, self.other_item.pk)
        result = self.client.get(reverse('projects:delivery-data', args=[self.south.pk])).json()
        self.assertEqual(result['recordsTotal'], 1)
        self.assertIn(reverse('inventory:correct', args=[self.south.pk, self.other_item.pk, replacement.pk]), result['data'][0]['actions'])
        self.assertContains(self.client.get(replacement.get_absolute_url()), destination.get_absolute_url())

    def test_common_entry_correction_and_legacy_delivery_cannot_consume_reservations(self):
        request = self.request(2)
        with self.assertRaises(ValidationError):
            correct_record(None, self.opening.pk, data(1, reason='Reducir entrada'))
        self.opening.refresh_from_db()
        self.assertIsNone(self.opening.voided_at)
        opening = open_stock(self.north, self.other_item, data(3))
        self.request(3, item=self.other_item)
        with self.assertRaises(ValidationError):
            deliver_stock(self.north, self.other_item, data(1, worker_full_name='Otra persona'))
        self.assertEqual(opening.position.balance, 3)
        self.assertEqual(request.reserved_quantity, 2)

    def test_request_creation_retry_and_event_failure_leave_no_partial_reservation(self):
        payload = data()
        request = create_request(self.north, self.item, payload)
        self.assertEqual(create_request(self.north, self.item, payload).pk, request.pk)
        self.assertEqual(request.events.count(), 1)
        with self.assertRaises(ValidationError):
            create_request(self.south, self.item, payload)
        with patch.object(StockRequestEvent.objects, 'create', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                self.request(item=self.other_item)
        self.assertEqual(StockRequest.objects.count(), 1)
        self.assertEqual(available_quantity(self.other_item.pk), 0)

    def test_form_scope_csrf_and_quantity_validation(self):
        url = reverse('requests:create', args=[self.north.pk])
        invalid = self.client.post(url, {**data(0), 'item': self.item.pk})
        self.assertIn('quantity', invalid.context['form'].errors)
        self.assertFalse(StockRequest.objects.exists())
        response = self.client.post(url, {**data(5), 'item': self.item.pk})
        request = StockRequest.objects.get()
        self.assertRedirects(response, request.get_absolute_url())
        self.assertContains(self.client.get(response.url), 'Necesidad de compra')
        self.assertEqual(self.client.get(reverse('requests:detail', args=[self.south.pk, request.pk])).status_code, 404)
        self.assertEqual(Client(enforce_csrf_checks=True).post(url, {**data(5), 'item': self.item.pk}).status_code, 403)
        result = self.client.get(reverse('requests:data', args=[self.north.pk])).json()
        self.assertEqual(result['data'][0]['purchase'], '3')
        self.assertIn('Confirmar entrega', result['data'][0]['actions'])
        other = self.client.get(reverse('requests:data', args=[self.south.pk])).json()
        self.assertEqual(other['recordsTotal'], 0)

    def test_request_detail_queries_do_not_grow_with_replaced_deliveries(self):
        receive_common_stock(self.item, data(18))
        request = self.request(20)

        def add_replaced_delivery(index):
            original = StockRecord.objects.create(
                position=self.opening.position, stock_request=request,
                operation=StockRecord.Operation.DELIVERY, quantity=1,
                occurred_on=date.today(), worker_full_name=f'Original {index}',
                voided_at=timezone.now(), void_reason='Corrección de prueba',
            )
            StockRecord.objects.create(
                position=self.opening.position, stock_request=request,
                operation=StockRecord.Operation.DELIVERY, quantity=1,
                occurred_on=date.today(), worker_full_name=f'Reemplazo {index}', replaces=original,
            )

        add_replaced_delivery(0)
        with CaptureQueriesContext(connection) as one_pair_queries:
            self.client.get(request.get_absolute_url())
        for index in range(1, 10):
            add_replaced_delivery(index)
        with CaptureQueriesContext(connection) as ten_pair_queries:
            response = self.client.get(request.get_absolute_url())

        self.assertEqual(len(ten_pair_queries), len(one_pair_queries))
        self.assertContains(response, 'Sustituido', count=10)
        self.assertContains(response, 'Vigente', count=10)

    def test_failure_after_delivery_or_replacement_write_rolls_back_every_change(self):
        request = self.request(2)
        with patch('inventory.request_services.ensure_available', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                deliver_request(request, data(2, worker_full_name='Ana Pérez'))
        self.assertEqual(request.delivered_quantity, 0)
        self.assertEqual(self.counts(), ('0', '0'))
        original = deliver_request(request, data(2, worker_full_name='Ana Pérez'))
        with patch('inventory.request_services.ensure_available', side_effect=RuntimeError('fallo simulado')):
            with self.assertRaises(RuntimeError):
                correct_record(self.north, original.pk, data(1, destination_request=request,
                    worker_full_name='Luis Soto', reason='Error'))
        original.refresh_from_db()
        self.assertIsNone(original.voided_at)
        self.assertFalse(StockRecord.objects.filter(replaces=original).exists())
        self.assertEqual((request.delivered_quantity, request.reserved_quantity), (2, 0))
        self.assertEqual(self.counts(), ('0', '2'))

    def test_request_table_search_and_order_cover_all_pages_without_cross_project_leak(self):
        for index in range(12):
            self.request(index + 1, observation=f'Pedido {index:02d}')
        self.request(100, project=self.south, observation='Pedido privado')
        url = reverse('requests:data', args=[self.north.pk])
        result = self.client.get(url, {'start': 0, 'length': 10, 'order[0][column]': 2,
                                      'order[0][dir]': 'asc'}).json()
        self.assertEqual(result['recordsTotal'], 12)
        self.assertEqual([int(row['quantity']) for row in result['data']], list(range(1, 11)))
        result = self.client.get(url, {'search[value]': 'Pedido 11'}).json()
        self.assertEqual(result['recordsFiltered'], 1)
        self.assertEqual(result['data'][0]['quantity'], '12')
        self.assertIn('Ver solicitud', result['data'][0]['actions'])
        self.assertEqual(self.client.get(url, {'search[value]': 'Pedido privado'}).json()['recordsFiltered'], 0)

    def test_database_constraints_for_allocations_and_ledger_links(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockRequest.objects.create(project=self.north, item=self.item, quantity=2, allocated_quantity=3, occurred_on=date.today())
        request = self.request()
        with self.assertRaises(IntegrityError), transaction.atomic():
            StockRecord.objects.create(position=self.opening.position, stock_request=request, operation='receipt', quantity=1, occurred_on=date.today())


class RequestConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        receive_common_stock(self.item, data(5))

    def concurrent(self, actions):
        barrier = Barrier(len(actions))
        def execute(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action().pk
                except ValidationError:
                    return 'rejected'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=len(actions)) as executor:
            return list(executor.map(execute, actions))

    def test_two_projects_cannot_reserve_the_same_units(self):
        self.concurrent([lambda: create_request(self.north, self.item, data(4)), lambda: create_request(self.south, self.item, data(4))])
        self.assertEqual(sorted(StockRequest.objects.values_list('allocated_quantity', flat=True)), [1, 4])
        self.assertEqual(available_quantity(self.item.pk), 0)
        self.assertEqual(reserved_quantity(self.item.pk), 5)

    def test_parallel_creation_retry_has_one_request(self):
        payload = data(3)
        ids = self.concurrent([lambda: create_request(self.north, self.item, payload)] * 2)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(StockRequest.objects.count(), 1)
        self.assertEqual(StockRequestEvent.objects.count(), 1)
        self.assertEqual(available_quantity(self.item.pk), 2)

    def test_parallel_delivery_retry_deducts_once(self):
        request = create_request(self.north, self.item, data(2))
        payload = data(2, worker_full_name='Ana Pérez')
        ids = self.concurrent([lambda: deliver_request(request, payload)] * 2)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(request.delivered_quantity, 2)
        self.assertEqual(StockPosition.common_balance(self.item.pk), 3)
        self.assertEqual(available_quantity(self.item.pk), 3)

    def test_parallel_reserve_more_cannot_duplicate_allocation(self):
        request = create_request(self.north, self.item, data(8))
        receive_common_stock(self.item, data(2))
        result = self.concurrent([lambda: reserve_more(request, data())] * 2)
        self.assertEqual(result.count('rejected'), 1)
        request.refresh_from_db()
        self.assertEqual(request.allocated_quantity, 7)
        self.assertEqual(available_quantity(self.item.pk), 0)

    def test_parallel_cancellation_of_requested_delivery_returns_one_reservation(self):
        request = create_request(self.north, self.item, data(2))
        record = deliver_request(request, data(2, worker_full_name='Ana Pérez'))
        def cancel():
            return cancel_delivery(self.north, record.pk, 'Registro equivocado')[0]
        self.concurrent([cancel, cancel])
        self.assertEqual((request.delivered_quantity, request.reserved_quantity), (0, 2))
        self.assertEqual(StockPosition.common_balance(self.item.pk), 5)
        self.assertEqual(available_quantity(self.item.pk), 3)

    def test_parallel_reduction_and_confirmation_preserve_actual_deliveries(self):
        request = create_request(self.north, self.item, data(2))
        self.concurrent([lambda: reduce_request(request, data(pending_quantity=0, reason='No se necesita')),
                         lambda: deliver_request(request, data(1, worker_full_name='Ana Pérez'))])
        request.refresh_from_db()
        self.assertEqual(request.pending_quantity, 0)
        self.assertEqual(request.allocated_quantity, request.delivered_quantity)
        self.assertEqual(available_quantity(self.item.pk), 5 - request.delivered_quantity)

    def test_parallel_distinct_confirmations_cannot_deliver_the_same_pending_twice(self):
        request = create_request(self.north, self.item, data(5))
        results = self.concurrent([lambda: deliver_request(request, data(5, worker_full_name='Ana Pérez'))] * 2)
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(request.delivered_quantity, 5)
        self.assertEqual(available_quantity(self.item.pk), 0)
        self.assertEqual(StockRecord.objects.filter(stock_request=request).count(), 1)

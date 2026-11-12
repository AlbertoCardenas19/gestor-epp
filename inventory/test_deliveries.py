import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from catalog.models import Item
from projects.models import Project

from .models import StockPosition, StockRecord
from .services import correct_record, deliver_stock, open_stock, receive_stock


def data(quantity=3, **overrides):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **overrides}


class DirectDeliveryTests(TestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Obra Norte')
        self.other = Project.objects.create(name='Obra Sur')
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        self.opening = open_stock(self.project, self.item, data(10))

    def url(self, name, *extra, project=None):
        return reverse(f'inventory:{name}', args=[(project or self.project).pk, self.item.pk, *extra])

    def deliver(self, quantity=3, **extra):
        return deliver_stock(self.project, self.item, data(quantity, worker_full_name='Ana Pérez', **extra))

    def test_delivery_records_worker_and_deducts_only_its_project(self):
        other_opening = open_stock(self.other, self.item, data(4))
        record = self.deliver(3)
        self.assertEqual(record.quantity, 3)
        self.assertEqual(record.delta, -3)
        self.assertEqual(record.worker_full_name, 'Ana Pérez')
        self.assertEqual(record.recorded_by, 'Prevencionista')
        self.assertEqual(record.position.balance, 7)
        self.assertEqual(other_opening.position.balance, 4)
        self.assertEqual(Item.objects.count(), 1)

    def test_form_creates_delivery_and_both_queries_use_the_new_balance(self):
        payload = data(3, worker_full_name='  Ana Pérez  ', observation='Entrega directa')
        response = self.client.post(self.url('deliver'), payload)
        self.assertEqual(response.status_code, 302)
        record = StockRecord.objects.get(operation='delivery')
        self.assertEqual(record.worker_full_name, 'Ana Pérez')
        history = Client().get(response.url)
        self.assertContains(history, 'data-testid="balance">7</p>')
        self.assertContains(history, 'Ana Pérez')
        self.assertContains(history, 'Entrega directa')
        listing = self.client.get(reverse('inventory:list', args=[self.project.pk]))
        self.assertEqual(listing.context['rows'][0]['position'].total, 7)

    def test_can_deliver_exact_balance_then_rejects_more(self):
        self.deliver(10)
        self.assertEqual(self.opening.position.balance, 0)
        with self.assertRaisesMessage(ValidationError, 'supera el saldo'):
            self.deliver(1)
        self.assertEqual(StockRecord.objects.count(), 2)

    def test_excess_delivery_preserves_form_and_does_not_write(self):
        payload = data(11, worker_full_name='Ana Pérez', observation='Conservar esta información')
        response = self.client.post(self.url('deliver'), payload)
        self.assertContains(response, 'supera el saldo disponible')
        self.assertContains(response, 'Ana Pérez')
        self.assertContains(response, 'Conservar esta información')
        self.assertEqual(StockRecord.objects.count(), 1)
        self.assertEqual(self.opening.position.balance, 10)
        payload['quantity'] = 2
        self.assertEqual(self.client.post(self.url('deliver'), payload).status_code, 302)
        self.assertEqual(self.opening.position.balance, 8)

    def test_worker_name_is_required_and_trimmed(self):
        for name in ['', '   ']:
            response = self.client.post(self.url('deliver'), data(worker_full_name=name))
            self.assertIn('worker_full_name', response.context['form'].errors)
        self.assertEqual(StockRecord.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.deliver_without_worker()

    def deliver_without_worker(self):
        return deliver_stock(self.project, self.item, data())

    def test_zero_negative_fractional_and_invalid_date_are_rejected(self):
        for quantity in [0, -1, '1.5']:
            response = self.client.post(self.url('deliver'), data(quantity, worker_full_name='Ana Pérez'))
            self.assertIn('quantity', response.context['form'].errors)
        response = self.client.post(self.url('deliver'), data(worker_full_name='Ana Pérez', occurred_on='2026-02-30'))
        self.assertIn('occurred_on', response.context['form'].errors)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_observation_is_optional_and_author_cannot_be_spoofed(self):
        response = self.client.post(self.url('deliver'), data(worker_full_name='Ana Pérez', recorded_by='Otra persona'))
        self.assertEqual(response.status_code, 302)
        record = StockRecord.objects.get(operation='delivery')
        self.assertEqual(record.observation, '')
        self.assertEqual(record.recorded_by, 'Prevencionista')

    def test_delivery_requires_opening_in_the_selected_project(self):
        response = self.client.get(self.url('deliver', project=self.other))
        self.assertContains(response, 'Registra primero la existencia inicial')
        response = self.client.post(self.url('deliver', project=self.other), data(worker_full_name='Ana Pérez'))
        self.assertEqual(response.status_code, 200)
        with self.assertRaisesMessage(ValidationError, 'Registra primero'):
            deliver_stock(self.other, self.item, data(worker_full_name='Ana Pérez'))
        self.assertEqual(StockPosition.objects.count(), 1)

    def test_same_form_submission_does_not_deduct_twice(self):
        payload = data(10, worker_full_name='Ana Pérez')
        for _ in range(2):
            self.assertEqual(self.client.post(self.url('deliver'), payload).status_code, 302)
        self.assertEqual(StockRecord.objects.filter(operation='delivery').count(), 1)
        self.assertEqual(self.opening.position.balance, 0)
        payload['worker_full_name'] = 'Luis Soto'
        response = self.client.post(self.url('deliver'), payload)
        self.assertContains(response, 'Este formulario ya se utilizó')
        self.assertEqual(StockRecord.objects.filter(operation='delivery').count(), 1)

    def test_history_escapes_worker_name(self):
        deliver_stock(self.project, self.item, data(worker_full_name='<script>alert(1)</script>'))
        response = self.client.get(self.url('history'))
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_delivery_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(self.url('deliver'), data(worker_full_name='Ana Pérez'))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(StockRecord.objects.count(), 1)

    def test_invalid_project_or_item_is_not_found(self):
        for url in [reverse('inventory:deliver', args=[99999, self.item.pk]), reverse('inventory:deliver', args=[self.project.pk, 99999])]:
            self.assertEqual(self.client.get(url).status_code, 404)

    def test_opening_correction_cannot_leave_less_than_already_delivered(self):
        self.deliver(8)
        with self.assertRaisesMessage(ValidationError, 'saldo negativo'):
            correct_record(self.project, self.opening.pk, data(7, reason='Nuevo conteo'))
        self.opening.refresh_from_db()
        self.assertIsNone(self.opening.voided_at)
        self.assertEqual(self.opening.quantity, 10)
        self.assertEqual(self.opening.position.balance, 2)
        self.assertEqual(StockRecord.objects.count(), 2)
        correct_record(self.project, self.opening.pk, data(8, reason='Conteo confirmado'))
        self.assertEqual(self.opening.position.balance, 0)

    def test_receipt_correction_cannot_leave_negative_balance(self):
        receipt = receive_stock(self.project, self.item, data(5))
        self.deliver(12)
        response = self.client.post(self.url('correct', receipt.pk), data(1, reason='Error en la entrada'))
        self.assertContains(response, 'saldo negativo')
        receipt.refresh_from_db()
        self.assertIsNone(receipt.voided_at)
        self.assertEqual(self.opening.position.balance, 3)
        self.assertEqual(StockRecord.objects.count(), 3)

    def test_delivery_correction_requires_complete_destination_data(self):
        delivery = self.deliver()
        self.assertEqual(self.client.get(self.url('correct', delivery.pk)).status_code, 200)
        with self.assertRaises(ValidationError):
            correct_record(self.project, delivery.pk, data(2, reason='Cambio'))
        self.assertEqual(self.opening.position.balance, 7)

    def test_database_requires_worker_and_positive_delivery_quantity(self):
        for quantity, worker in [(0, 'Ana Pérez'), (-1, 'Ana Pérez'), (1, ''), (1, '   ')]:
            with self.subTest(quantity=quantity, worker=worker):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    StockRecord.objects.create(position=self.opening.position, operation='delivery', quantity=quantity,
                                               occurred_on=date(2026, 11, 12), worker_full_name=worker)


class DeliveryConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.project = Project.objects.create(name='Proyecto concurrente')
        self.item = Item.objects.create(name='Casco', item_type=Item.Type.EPP)
        self.opening = open_stock(self.project, self.item, data(10))

    def concurrent(self, actions):
        barrier = Barrier(2)

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return action().pk
                except ValidationError:
                    return 'rejected'
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, actions))

    def test_parallel_deliveries_do_not_overspend(self):
        results = self.concurrent([
            lambda: deliver_stock(self.project, self.item, data(7, worker_full_name='Ana Pérez')),
            lambda: deliver_stock(self.project, self.item, data(7, worker_full_name='Luis Soto')),
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(self.opening.position.balance, 3)
        self.assertEqual(StockRecord.objects.filter(operation='delivery').count(), 1)

    def test_parallel_resubmission_deducts_once(self):
        payload = data(4, worker_full_name='Ana Pérez')
        results = self.concurrent([
            lambda: deliver_stock(self.project, self.item, payload),
            lambda: deliver_stock(self.project, self.item, payload),
        ])
        self.assertEqual(results[0], results[1])
        self.assertEqual(self.opening.position.balance, 6)
        self.assertEqual(StockRecord.objects.filter(operation='delivery').count(), 1)

    def test_correction_and_delivery_cannot_make_balance_negative(self):
        results = self.concurrent([
            lambda: correct_record(self.project, self.opening.pk, data(1, reason='Conteo revisado')),
            lambda: deliver_stock(self.project, self.item, data(8, worker_full_name='Ana Pérez')),
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.assertIn(self.opening.position.balance, [1, 2])

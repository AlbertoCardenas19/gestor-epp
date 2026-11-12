import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from catalog.models import Item
from projects.models import Project

from .models import StockPosition, StockRecord
from .services import cancel_delivery, correct_delivery, deliver_stock, open_stock


def data(quantity=4, **extra):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **extra}


class DeliveryCancellationTests(TestCase):
    def setUp(self):
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        self.helmet = Item.objects.create(name='Casco', item_type='epp')
        self.gloves = Item.objects.create(name='Guantes', item_type='epp')
        self.source = open_stock(self.north, self.helmet, data(10)).position
        self.target = open_stock(self.south, self.gloves, data(8)).position
        self.delivery = deliver_stock(self.north, self.helmet, data(4, worker_full_name='Ana Pérez', observation='Original'))

    def url(self, record=None, project=None, item=None):
        return reverse('inventory:cancel', args=[(project or self.north).pk, (item or self.helmet).pk,
                                                (record or self.delivery).pk])

    def correction(self):
        return data(3, destination_project=self.south, destination_item=self.gloves,
                    worker_full_name='Luis Soto', reason='Proyecto y elemento equivocados')

    def assert_current(self):
        self.delivery.refresh_from_db()
        self.assertIsNone(self.delivery.voided_at)
        self.assertEqual(self.delivery.void_reason, '')
        self.assertEqual((self.source.balance, self.target.balance), (6, 8))

    def test_cancels_current_delivery_without_changing_original_data(self):
        fields = ['position_id', 'worker_full_name', 'quantity', 'occurred_on', 'observation',
                  'created_at', 'recorded_by', 'operation', 'submission_key']
        before = {field: getattr(self.delivery, field) for field in fields}
        count = StockRecord.objects.count()
        cancelled, changed = cancel_delivery(self.north, self.delivery.pk, '  Registro duplicado  ')
        self.assertTrue(changed)
        self.delivery.refresh_from_db()
        self.assertEqual({field: getattr(self.delivery, field) for field in fields}, before)
        self.assertIsNotNone(self.delivery.voided_at)
        self.assertEqual(self.delivery.void_reason, 'Registro duplicado')
        self.assertTrue(cancelled.is_cancelled)
        self.assertFalse(cancelled.is_replaced)
        self.assertEqual((self.source.balance, self.target.balance), (10, 8))
        self.assertEqual(StockRecord.objects.count(), count)
        self.assertFalse(StockRecord.objects.filter(replaces=self.delivery).exists())

    def test_cancels_replacement_in_its_current_project_and_item(self):
        replacement = correct_delivery(self.north, self.delivery.pk, self.correction())
        self.delivery.refresh_from_db()
        correction_date, correction_reason = self.delivery.voided_at, self.delivery.void_reason
        self.assertEqual((self.source.balance, self.target.balance), (10, 5))
        cancel_delivery(self.south, replacement.pk, 'Entrega correcta registrada dos veces')
        replacement.refresh_from_db()
        self.delivery.refresh_from_db()
        self.assertEqual((self.source.balance, self.target.balance), (10, 8))
        self.assertTrue(replacement.is_cancelled)
        self.assertTrue(self.delivery.is_replaced)
        self.assertEqual(self.delivery.voided_at, correction_date)
        self.assertEqual(self.delivery.void_reason, correction_reason)
        self.assertEqual(replacement.replaces_id, self.delivery.pk)

    def test_rejects_replaced_original_even_if_replacement_was_cancelled(self):
        replacement = correct_delivery(self.north, self.delivery.pk, self.correction())
        for stage in ['before', 'after']:
            if stage == 'after':
                cancel_delivery(self.south, replacement.pk, 'Registro equivocado')
            before = (self.source.balance, self.target.balance)
            with self.assertRaisesMessage(ValidationError, 'fue sustituido'):
                cancel_delivery(self.north, self.delivery.pk, 'Anular original')
            self.assertEqual((self.source.balance, self.target.balance), before)
        self.assertEqual(StockRecord.objects.count(), 4)

    def test_reason_is_required_in_service_and_form(self):
        for reason in ['', '   ']:
            with self.subTest(reason=reason):
                with self.assertRaisesMessage(ValidationError, 'motivo'):
                    cancel_delivery(self.north, self.delivery.pk, reason)
                response = self.client.post(self.url(), {'reason': reason})
                self.assertFormError(response.context['form'], 'reason', 'Escribe el motivo de la anulación.')
                self.assertContains(response, 'aria-invalid="true"')
                self.assert_current()

    def test_repeated_requests_preserve_reason_date_and_balance(self):
        cancel_delivery(self.north, self.delivery.pk, 'Registro duplicado')
        self.delivery.refresh_from_db()
        first_date = self.delivery.voided_at
        record, changed = cancel_delivery(self.north, self.delivery.pk, 'Otro motivo')
        self.assertFalse(changed)
        self.assertEqual(record.void_reason, 'Registro duplicado')
        self.assertEqual(record.voided_at, first_date)
        self.assertEqual(self.source.balance, 10)
        self.assertEqual(StockRecord.objects.count(), 3)

    def test_confirmation_get_does_not_cancel(self):
        response = self.client.get(self.url())
        self.assertContains(response, 'Confirmar anulación')
        self.assertContains(response, 'no registra una devolución física')
        self.assert_current()

    def test_post_and_repeated_post_show_history_without_refunding_twice(self):
        for n in range(2):
            response = self.client.post(self.url(), {'reason': 'Registro duplicado'})
            self.assertRedirects(response, self.delivery.get_absolute_url())
            history = self.client.get(response.url)
            self.assertContains(history, 'data-testid="balance">10</p>')
            self.assertContains(history, 'Anulado')
            self.assertContains(history, 'Registro duplicado')
            self.assertContains(history, 'Anulado el')
            self.assertContains(history, 'Trabajador destinatario:')
            self.assertContains(history, 'Ana Pérez')
            self.assertNotContains(history, 'Ver reemplazo')
            self.assertNotContains(history, 'Anular entrega')
        self.assertEqual(StockRecord.objects.count(), 3)
        self.assertEqual(self.source.balance, 10)

    def test_substituted_original_has_no_cancellation_form(self):
        replacement = correct_delivery(self.north, self.delivery.pk, self.correction())
        get = self.client.get(self.url())
        self.assertContains(get, 'fue sustituido')
        self.assertContains(get, replacement.get_absolute_url())
        self.assertNotContains(get, 'Confirmar anulación')
        post = self.client.post(self.url(), {'reason': 'Intento sobre el original'})
        self.assertContains(post, 'fue sustituido')
        self.assertEqual((self.source.balance, self.target.balance), (10, 5))

    def test_cancelled_record_has_no_confirmation_form(self):
        cancel_delivery(self.north, self.delivery.pk, 'Registro duplicado')
        response = self.client.get(self.url())
        self.assertContains(response, 'ya está anulada')
        self.assertContains(response, 'Registro duplicado')
        self.assertNotContains(response, 'Confirmar anulación')

    def test_cannot_correct_a_cancelled_delivery(self):
        cancel_delivery(self.north, self.delivery.pk, 'Registro equivocado')
        with self.assertRaisesMessage(ValidationError, 'está anulada'):
            correct_delivery(self.north, self.delivery.pk, self.correction())
        url = reverse('inventory:correct', args=[self.north.pk, self.helmet.pk, self.delivery.pk])
        response = self.client.get(url)
        self.assertContains(response, 'está anulada')
        self.assertNotContains(response, 'Guardar corrección')
        self.assertEqual((self.source.balance, self.target.balance), (10, 8))

    def test_cannot_cancel_opening_or_use_wrong_project_item(self):
        opening = self.source.records.get(operation='opening')
        with self.assertRaisesMessage(ValidationError, 'Solo se pueden'):
            cancel_delivery(self.north, opening.pk, 'Intento inválido')
        for url in [self.url(record=opening), self.url(project=self.south), self.url(item=self.gloves)]:
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'reason': 'Intento inválido'}).status_code, 404)
        self.assert_current()

    def test_cancellation_requires_csrf(self):
        response = Client(enforce_csrf_checks=True).post(self.url(), {'reason': 'Registro duplicado'})
        self.assertEqual(response.status_code, 403)
        self.assert_current()

    def test_post_cannot_change_refunded_quantity_or_destination(self):
        self.client.post(self.url(), {'reason': 'Registro duplicado', 'quantity': 999,
                                     'destination_project': self.south.pk, 'destination_item': self.gloves.pk})
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.quantity, 4)
        self.assertEqual(self.delivery.position_id, self.source.pk)
        self.assertEqual((self.source.balance, self.target.balance), (10, 8))

    def test_reason_is_escaped_in_history(self):
        cancel_delivery(self.north, self.delivery.pk, '<script>alert(1)</script>')
        response = self.client.get(self.delivery.get_absolute_url())
        self.assertContains(response, '&lt;script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')

    def test_exception_after_database_update_rolls_back_cancellation(self):
        original_save = StockRecord.save

        def fail_after_update(record, *args, **kwargs):
            original_save(record, *args, **kwargs)
            raise RuntimeError('Fallo simulado después de escribir')

        with patch.object(StockRecord, 'save', new=fail_after_update):
            with self.assertRaisesMessage(RuntimeError, 'Fallo simulado'):
                cancel_delivery(self.north, self.delivery.pk, 'Registro duplicado')
        self.assert_current()
        self.assertEqual(StockRecord.objects.count(), 3)
        _, changed = cancel_delivery(self.north, self.delivery.pk, 'Reintento válido')
        self.assertTrue(changed)
        self.assertEqual(self.source.balance, 10)


class DeliveryCancellationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        self.item = Item.objects.create(name='Casco', item_type='epp')
        self.source = open_stock(self.north, self.item, data(10)).position
        self.target = open_stock(self.south, self.item, data(8)).position
        self.delivery = deliver_stock(self.north, self.item, data(4, worker_full_name='Ana Pérez'))

    def concurrent(self, actions):
        barrier = Barrier(2)

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                try:
                    return action()
                except ValidationError:
                    return 'rejected'
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, actions))

    def test_simultaneous_cancellations_refund_once(self):
        results = self.concurrent([
            lambda: cancel_delivery(self.north, self.delivery.pk, 'Primer motivo')[1],
            lambda: cancel_delivery(self.north, self.delivery.pk, 'Segundo motivo')[1],
        ])
        self.assertCountEqual(results, [True, False])
        self.assertEqual(self.source.balance, 10)
        self.assertEqual(StockRecord.objects.count(), 3)

    def test_cancellation_and_correction_cannot_both_apply(self):
        results = self.concurrent([
            lambda: cancel_delivery(self.north, self.delivery.pk, 'Registro equivocado')[1],
            lambda: correct_delivery(self.north, self.delivery.pk, data(
                3, destination_project=self.south, destination_item=self.item,
                worker_full_name='Luis Soto', reason='Proyecto correcto',
            )).pk,
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.delivery.refresh_from_db()
        if self.delivery.is_cancelled:
            self.assertEqual((self.source.balance, self.target.balance), (10, 8))
            self.assertEqual(StockRecord.objects.count(), 3)
        else:
            self.assertTrue(self.delivery.is_replaced)
            self.assertEqual((self.source.balance, self.target.balance), (10, 5))
            self.assertEqual(StockRecord.objects.count(), 4)

    def test_cancellation_and_new_delivery_keep_coherent_balance(self):
        self.concurrent([
            lambda: cancel_delivery(self.north, self.delivery.pk, 'Registro duplicado')[1],
            lambda: deliver_stock(self.north, self.item, data(8, worker_full_name='Luis Soto')).pk,
        ])
        self.delivery.refresh_from_db()
        self.assertTrue(self.delivery.is_cancelled)
        self.assertIn(self.source.balance, [2, 10])
        self.assertEqual(StockRecord.objects.filter(pk=self.delivery.pk).count(), 1)

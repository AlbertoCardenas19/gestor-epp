import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from catalog.models import Item
from projects.models import Project

from .models import StockPosition, StockRecord
from .services import correct_delivery, correct_record, deliver_stock, open_stock


def data(quantity=5, **extra):
    return {'quantity': quantity, 'occurred_on': date(2026, 11, 12), 'observation': '',
            'submission_key': uuid.uuid4(), **extra}


class DeliveryCorrectionTests(TestCase):
    def setUp(self):
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        self.helmet = Item.objects.create(name='Casco', item_type='epp')
        self.gloves = Item.objects.create(name='Guantes', item_type='epp')
        self.source = open_stock(self.north, self.helmet, data(20)).position
        self.target = open_stock(self.south, self.gloves, data(8)).position
        self.original = deliver_stock(self.north, self.helmet, data(5, worker_full_name='Ana Pérez', observation='Original'))
        self.url = reverse('inventory:correct', args=[self.north.pk, self.helmet.pk, self.original.pk])

    def correction(self, **extra):
        return data(3, destination_project=self.south, destination_item=self.gloves,
                    worker_full_name='Luis Soto', reason='Registro equivocado', **extra)

    def payload(self, **extra):
        values = self.correction()
        values.update(extra)
        values['destination_project'] = getattr(values['destination_project'], 'pk', values['destination_project'])
        values['destination_item'] = getattr(values['destination_item'], 'pk', values['destination_item'])
        return values

    def assert_unchanged(self):
        self.original.refresh_from_db()
        self.assertIsNone(self.original.voided_at)
        self.assertEqual(self.original.void_reason, '')
        self.assertEqual(self.source.balance, 15)
        self.assertEqual(self.target.balance, 8)
        self.assertEqual(StockRecord.objects.count(), 3)

    def test_corrects_all_six_fields_and_preserves_original(self):
        captured_at = self.original.created_at
        replacement = correct_record(self.north, self.original.pk,
                                     self.correction(occurred_on=date(2026, 11, 10), observation='Corregida'))
        self.original.refresh_from_db()
        self.assertEqual(self.original.position_id, self.source.pk)
        self.assertEqual(self.original.worker_full_name, 'Ana Pérez')
        self.assertEqual(self.original.quantity, 5)
        self.assertEqual(self.original.occurred_on, date(2026, 11, 12))
        self.assertEqual(self.original.observation, 'Original')
        self.assertEqual(self.original.created_at, captured_at)
        self.assertIsNotNone(self.original.voided_at)
        self.assertEqual(self.original.void_reason, 'Registro equivocado')
        self.assertEqual(replacement.replaces_id, self.original.pk)
        self.assertEqual(replacement.position_id, self.target.pk)
        self.assertEqual(replacement.worker_full_name, 'Luis Soto')
        self.assertEqual(replacement.quantity, 3)
        self.assertEqual(replacement.occurred_on, date(2026, 11, 10))
        self.assertEqual(replacement.observation, 'Corregida')
        self.assertGreaterEqual(replacement.created_at, captured_at)
        self.assertEqual((self.source.balance, self.target.balance), (20, 5))

    def test_same_position_uses_credit_from_original_quantity(self):
        replacement = correct_delivery(self.north, self.original.pk, {
            **self.correction(), 'destination_project': self.north, 'destination_item': self.helmet, 'quantity': 18,
        })
        self.assertEqual(replacement.position_id, self.source.pk)
        self.assertEqual(self.source.balance, 2)
        self.assertEqual(self.target.balance, 8)

    def test_reducing_quantity_releases_only_the_difference(self):
        correct_delivery(self.north, self.original.pk, {
            **self.correction(), 'destination_project': self.north, 'destination_item': self.helmet,
        })
        self.assertEqual(self.source.balance, 17)

    def test_changing_only_person_date_observation_keeps_balances(self):
        correct_delivery(self.north, self.original.pk, {
            **self.correction(), 'destination_project': self.north, 'destination_item': self.helmet,
            'quantity': 5, 'occurred_on': date(2026, 11, 11), 'observation': 'Texto nuevo',
        })
        self.assertEqual((self.source.balance, self.target.balance), (15, 8))

    def test_can_change_only_project(self):
        target = open_stock(self.south, self.helmet, data(4)).position
        correct_delivery(self.north, self.original.pk, {**self.correction(), 'destination_item': self.helmet})
        self.assertEqual((self.source.balance, target.balance), (20, 1))

    def test_can_change_only_item(self):
        target = open_stock(self.north, self.gloves, data(4)).position
        correct_delivery(self.north, self.original.pk, {**self.correction(), 'destination_project': self.north})
        self.assertEqual((self.source.balance, target.balance), (20, 1))

    def test_target_without_opening_is_rejected_without_creating_position(self):
        with self.assertRaisesMessage(ValidationError, 'no tiene apertura'):
            correct_delivery(self.north, self.original.pk, {**self.correction(), 'destination_item': self.helmet})
        self.assert_unchanged()
        self.assertEqual(StockPosition.objects.count(), 2)

    def test_insufficient_target_balance_rolls_back_every_change(self):
        with self.assertRaisesMessage(ValidationError, 'saldo disponible'):
            correct_delivery(self.north, self.original.pk, {**self.correction(), 'quantity': 9})
        self.assert_unchanged()

    def test_missing_reason_and_invalid_replacement_roll_back_original(self):
        for extra in [{'reason': '   '}, {'quantity': 0}, {'worker_full_name': '   '}]:
            with self.subTest(extra=extra):
                with self.assertRaises(ValidationError):
                    correct_delivery(self.north, self.original.pk, {**self.correction(), **extra})
                self.assert_unchanged()

    def test_form_initializes_original_fields_and_submits_to_new_history(self):
        form = self.client.get(self.url).context['form']
        self.assertEqual(form['destination_project'].value(), self.north.pk)
        self.assertEqual(form['destination_item'].value(), self.helmet.pk)
        self.assertEqual(form['worker_full_name'].value(), 'Ana Pérez')
        response = self.client.post(self.url, self.payload())
        replacement = StockRecord.objects.get(replaces=self.original)
        self.assertRedirects(response, replacement.get_absolute_url())
        old = self.client.get(self.original.get_absolute_url())
        new = self.client.get(replacement.get_absolute_url())
        self.assertContains(old, 'Sustituido')
        self.assertContains(old, replacement.get_absolute_url())
        self.assertContains(old, 'Ana Pérez')
        self.assertContains(new, self.original.get_absolute_url())
        self.assertContains(new, 'Luis Soto')
        self.assertContains(new, 'data-testid="balance">5</p>')
        self.assertContains(old, 'data-testid="balance">20</p>')

    def test_invalid_forms_keep_inputs_and_do_not_write(self):
        for extra, field in [({'quantity': '1.5'}, 'quantity'), ({'quantity': 0}, 'quantity'),
                             ({'reason': ''}, 'reason'), ({'worker_full_name': ''}, 'worker_full_name'),
                             ({'occurred_on': '2026-02-30'}, 'occurred_on'),
                             ({'destination_project': 99999}, 'destination_project'),
                             ({'destination_item': 99999}, 'destination_item')]:
            with self.subTest(extra=extra):
                response = self.client.post(self.url, self.payload(observation='Conservar', **extra))
                self.assertIn(field, response.context['form'].errors)
                self.assertContains(response, 'Conservar')
                self.assert_unchanged()

    def test_service_rejection_keeps_form_inputs(self):
        response = self.client.post(self.url, self.payload(quantity=9, observation='Conservar'))
        self.assertContains(response, 'saldo disponible')
        self.assertContains(response, 'Conservar')
        self.assertContains(response, 'Luis Soto')
        self.assert_unchanged()

    def test_repeated_post_does_not_refund_or_deduct_twice(self):
        payload = self.payload()
        first = self.client.post(self.url, payload)
        second = self.client.post(self.url, payload)
        self.assertEqual(first.url, second.url)
        self.assertEqual((self.source.balance, self.target.balance), (20, 5))
        self.assertEqual(StockRecord.objects.count(), 4)
        payload['quantity'] = 4
        self.assertContains(self.client.post(self.url, payload), 'ya fue corregido')
        self.assertEqual((self.source.balance, self.target.balance), (20, 5))

    def test_stale_original_cannot_be_corrected_again(self):
        correct_delivery(self.north, self.original.pk, self.correction())
        with self.assertRaisesMessage(ValidationError, 'ya fue corregido'):
            correct_delivery(self.north, self.original.pk, self.correction())
        self.assertEqual(StockRecord.objects.count(), 4)

    def test_replacement_can_be_corrected_back_to_original_position(self):
        first = correct_delivery(self.north, self.original.pk, self.correction())
        last = correct_delivery(self.south, first.pk, {
            **self.correction(), 'destination_project': self.north, 'destination_item': self.helmet,
            'quantity': 2, 'reason': 'Segunda corrección', 'submission_key': uuid.uuid4(),
        })
        self.assertEqual(last.replaces_id, first.pk)
        self.assertEqual(first.replaces_id, self.original.pk)
        self.assertEqual((self.source.balance, self.target.balance), (18, 8))
        self.assertEqual(StockRecord.objects.filter(operation='delivery', voided_at__isnull=True).count(), 1)

    def test_wrong_original_scope_is_404(self):
        for project, item in [(self.south, self.helmet), (self.north, self.gloves)]:
            url = reverse('inventory:correct', args=[project.pk, item.pk, self.original.pk])
            self.assertEqual(self.client.post(url, self.payload()).status_code, 404)
        self.assert_unchanged()

    def test_csrf_is_required(self):
        response = Client(enforce_csrf_checks=True).post(self.url, self.payload())
        self.assertEqual(response.status_code, 403)
        self.assert_unchanged()

    def test_text_is_escaped_in_both_histories(self):
        replacement = correct_delivery(self.north, self.original.pk, {
            **self.correction(), 'worker_full_name': '<script>alert(1)</script>', 'reason': '<img src=x onerror=alert(1)>',
        })
        for url in [self.original.get_absolute_url(), replacement.get_absolute_url()]:
            response = self.client.get(url)
            self.assertNotContains(response, '<script>alert(1)</script>')
            self.assertNotContains(response, '<img src=x')


class DeliveryCorrectionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.north = Project.objects.create(name='Norte')
        self.south = Project.objects.create(name='Sur')
        self.item = Item.objects.create(name='Casco', item_type='epp')
        self.source = open_stock(self.north, self.item, data(20)).position
        self.target = open_stock(self.south, self.item, data(8)).position
        self.original = deliver_stock(self.north, self.item, data(5, worker_full_name='Ana Pérez'))

    def correction(self, **extra):
        values = data(3, destination_project=self.south, destination_item=self.item,
                      worker_full_name='Luis Soto', reason='Corrección')
        values.update(extra)
        return values

    def concurrent(self, actions):
        barrier = Barrier(2)

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                with connections['default'].cursor() as cursor:
                    cursor.execute("SET lock_timeout = '5s'")
                try:
                    return action().pk
                except ValidationError:
                    return 'rejected'
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(run, actions))

    def test_two_corrections_of_same_record_have_one_winner(self):
        results = self.concurrent([
            lambda: correct_delivery(self.north, self.original.pk, self.correction()),
            lambda: correct_delivery(self.north, self.original.pk, self.correction(quantity=4)),
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(self.source.balance, 20)
        self.assertIn(self.target.balance, [4, 5])
        self.assertEqual(StockRecord.objects.filter(replaces=self.original).count(), 1)

    def test_parallel_same_request_is_applied_once(self):
        payload = self.correction()
        results = self.concurrent([
            lambda: correct_delivery(self.north, self.original.pk, payload),
            lambda: correct_delivery(self.north, self.original.pk, payload),
        ])
        self.assertEqual(results[0], results[1])
        self.assertEqual((self.source.balance, self.target.balance), (20, 5))

    def test_opposite_cross_project_corrections_do_not_deadlock(self):
        other = deliver_stock(self.south, self.item, data(3, worker_full_name='Luis Soto'))
        results = self.concurrent([
            lambda: correct_delivery(self.north, self.original.pk, self.correction(quantity=2)),
            lambda: correct_delivery(self.south, other.pk, self.correction(destination_project=self.north, quantity=4)),
        ])
        self.assertNotIn('rejected', results)
        self.assertEqual((self.source.balance, self.target.balance), (16, 6))

    def test_correction_and_normal_delivery_cannot_overspend_target(self):
        results = self.concurrent([
            lambda: correct_delivery(self.north, self.original.pk, self.correction(quantity=6)),
            lambda: deliver_stock(self.south, self.item, data(6, worker_full_name='Otra persona')),
        ])
        self.assertEqual(results.count('rejected'), 1)
        self.assertEqual(self.target.balance, 2)
        self.assertIn(self.source.balance, [15, 20])

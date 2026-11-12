from django.db import models
from django.urls import reverse


class Item(models.Model):
    class Type(models.TextChoices):
        EPP = 'epp', 'EPP'
        SIGNAGE = 'signage', 'Señalética'

    name = models.TextField('nombre')
    item_type = models.CharField('tipo', max_length=16, choices=Type.choices)
    description = models.TextField('descripción', blank=True)

    class Meta:
        ordering = ['pk']
        verbose_name = 'elemento'
        verbose_name_plural = 'elementos'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(item_type__in=['epp', 'signage']),
                name='catalog_item_valid_type',
            ),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('catalog:detail', kwargs={'pk': self.pk})

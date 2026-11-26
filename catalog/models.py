from django.contrib.postgres.aggregates import StringAgg
from django.db import models
from django.db.models.functions import Coalesce
from django.urls import reverse


class Category(models.Model):
    name = models.CharField('nombre', max_length=150, unique=True)

    class Meta:
        ordering = ['name', 'pk']

    def __str__(self):
        return self.name


class ItemQuerySet(models.QuerySet):
    def with_category_label(self):
        categories = Category.objects.filter(item=models.OuterRef('pk')).order_by().values('item').annotate(
            label=StringAgg('name', ', ', order_by='name'),
        ).values('label')
        return self.annotate(category_label=Coalesce(models.Subquery(categories), models.Value(''), output_field=models.TextField()))


class Item(models.Model):
    name = models.TextField('nombre')
    categories = models.ManyToManyField(Category, verbose_name='categorías')
    description = models.TextField('descripción', blank=True)

    objects = ItemQuerySet.as_manager()

    class Meta:
        ordering = ['pk']
        verbose_name = 'elemento'
        verbose_name_plural = 'elementos'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('stock:item', kwargs={'pk': self.pk})

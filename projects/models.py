from django.db import models
from django.urls import reverse
from django.utils import timezone
from zoneinfo import ZoneInfo


def project_creation_date():
    return timezone.localdate(timezone=ZoneInfo('America/Santiago'))


class Project(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = 'in_progress', 'En curso'
        FINISHED = 'finished', 'Terminado'

    name = models.TextField('nombre')
    description = models.TextField('descripción', blank=True)
    created_on = models.DateField('fecha de creación', null=True, blank=True, default=project_creation_date, editable=False)
    status = models.CharField('estado', max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

    class Meta:
        ordering = ['pk']
        verbose_name = 'proyecto'
        verbose_name_plural = 'proyectos'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:detail', kwargs={'pk': self.pk})

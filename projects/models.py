from django.db import models
from django.urls import reverse


class Project(models.Model):
    name = models.TextField('nombre')
    description = models.TextField('descripción', blank=True)

    class Meta:
        ordering = ['pk']
        verbose_name = 'proyecto'
        verbose_name_plural = 'proyectos'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('projects:detail', kwargs={'pk': self.pk})

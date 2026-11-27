from django.db import migrations, models
import projects.models


class Migration(migrations.Migration):
    dependencies = [('projects', '0001_initial')]

    operations = [
        # Existing projects have no reliable creation date; retain NULL.
        migrations.AddField(
            model_name='project', name='created_on',
            field=models.DateField(blank=True, editable=False, null=True, verbose_name='fecha de creación'),
        ),
        migrations.AlterField(
            model_name='project', name='created_on',
            field=models.DateField(blank=True, default=projects.models.project_creation_date, editable=False,
                                   null=True, verbose_name='fecha de creación'),
        ),
        migrations.AddField(
            model_name='project', name='status',
            field=models.CharField(choices=[('in_progress', 'En curso'), ('finished', 'Terminado')],
                                   default='in_progress', max_length=20, verbose_name='estado'),
        ),
    ]

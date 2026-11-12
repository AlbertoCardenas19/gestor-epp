from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField(verbose_name='nombre')),
                ('description', models.TextField(blank=True, verbose_name='descripción')),
            ],
            options={'verbose_name': 'proyecto', 'verbose_name_plural': 'proyectos', 'ordering': ['pk']},
        ),
    ]

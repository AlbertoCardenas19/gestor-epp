from django.db import migrations, models
from django.db.migrations.exceptions import IrreversibleError


def copy_categories(apps, schema_editor):
    db = schema_editor.connection.alias
    Category = apps.get_model('catalog', 'Category')
    Item = apps.get_model('catalog', 'Item')
    categories = {
        key: Category.objects.using(db).create(name=name)
        for key, name in [('epp', 'EPP'), ('signage', 'Señaléticas'), ('other', 'Otros')]
    }
    link = Item.categories.through
    batch = []
    for item_id, item_type in Item.objects.using(db).values_list('pk', 'item_type').iterator():
        batch.append(link(item_id=item_id, category_id=categories[item_type].pk))
        if len(batch) == 1000:
            link.objects.using(db).bulk_create(batch)
            batch.clear()
    link.objects.using(db).bulk_create(batch)


def restore_legacy_types(apps, schema_editor):
    Item = apps.get_model('catalog', 'Item')
    items = Item.objects.using(schema_editor.connection.alias)
    for name, legacy_type in [('EPP', 'epp'), ('Señaléticas', 'signage')]:
        items.filter(categories__name=name).update(item_type=legacy_type)
    if items.filter(item_type__isnull=True).exists():
        raise IrreversibleError('Hay elementos que el catálogo anterior no puede clasificar.')
    if items.exclude(categories__name__in=['EPP', 'Señaléticas']).exists() or items.annotate(
        category_count=models.Count('categories'),
    ).exclude(category_count=1).exists():
        raise IrreversibleError('Revertir descartaría clasificaciones múltiples.')


class Migration(migrations.Migration):
    dependencies = [('catalog', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='nombre')),
            ],
            options={'ordering': ['name', 'pk']},
        ),
        migrations.AddField(
            model_name='item', name='categories',
            field=models.ManyToManyField(to='catalog.category', verbose_name='categorías'),
        ),
        migrations.AlterField(
            model_name='item', name='item_type',
            field=models.CharField('tipo', max_length=16, choices=[('epp', 'EPP'), ('signage', 'Señalética')], null=True),
        ),
        migrations.RunPython(copy_categories, restore_legacy_types),
        migrations.RunSQL('SET CONSTRAINTS ALL IMMEDIATE', reverse_sql=migrations.RunSQL.noop),
        migrations.RemoveConstraint(model_name='item', name='catalog_item_valid_type'),
        migrations.RemoveField(model_name='item', name='item_type'),
    ]

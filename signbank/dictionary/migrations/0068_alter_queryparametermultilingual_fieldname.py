# Generated by Django 4.1.7 on 2023-04-06 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0067_alter_queryparametermultilingual_fieldname'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queryparametermultilingual',
            name='fieldName',
            field=models.CharField(choices=[('glosssearch', 'glosssearch'), ('lemma', 'lemma'), ('keyword', 'keyword'), ('tags', 'tags'), ('definitionContains', 'definitionContains'), ('createdBy', 'createdBy'), ('translation', 'translation')], max_length=20, verbose_name='Text Search Field'),
        ),
    ]

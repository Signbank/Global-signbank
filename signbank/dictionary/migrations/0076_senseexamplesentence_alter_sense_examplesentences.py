# Generated by Django 4.1.7 on 2023-08-22 14:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0075_alter_queryparameterboolean_fieldname'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.CreateModel(
                name='SenseExamplesentence',
                fields=[
                    ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('examplesentence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.examplesentence')),
                    ('sense', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.sense')),
                ],
                options={
                    'verbose_name': 'Sense exampleSentence',
                    'verbose_name_plural': 'Sense exampleSentences',
                    'db_table': 'dictionary_sense_exampleSentences',
                    'unique_together': {('sense', 'examplesentence')},
                },
            ),
            migrations.AlterField(
                model_name='sense',
                name='exampleSentences',
                field=models.ManyToManyField(help_text='Examplesentences in this Sense', related_name='senses', through='dictionary.SenseExamplesentence', to='dictionary.examplesentence', verbose_name='Example sentences'),
            ),
        ])
    ]

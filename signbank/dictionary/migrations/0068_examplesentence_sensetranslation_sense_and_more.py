# Generated by Django 4.1.7 on 2023-05-10 12:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0067_alter_queryparametermultilingual_fieldname'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExampleSentence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sentencetype', models.CharField(choices=[('declarative', 'Declarative (statement)'), ('interrogative', 'Interrogative (question)'), ('imperative', 'Imperative (command)'), ('exclamative', 'Exclamative (exclamation)')], default='declarative', max_length=32)),
                ('negative', models.BooleanField(default=False)),
                ('video', models.TextField(default='zin_over_iets.mp4', max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='SenseTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('keywords', models.ManyToManyField(to='dictionary.keyword')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.language')),
            ],
        ),
        migrations.CreateModel(
            name='Sense',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orderindex', models.IntegerField(default=0)),
                ('dataset', models.ForeignKey(default=5, help_text='Dataset a sense is part of', null=True, on_delete=django.db.models.deletion.CASCADE, to='dictionary.dataset', verbose_name='Dataset')),
                ('exampleSentences', models.ManyToManyField(to='dictionary.examplesentence')),
                ('senseTranslations', models.ManyToManyField(to='dictionary.sensetranslation')),
            ],
            options={
                'ordering': ['orderindex'],
            },
        ),
        migrations.CreateModel(
            name='ExampleSentenceTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('examplesentence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.examplesentence')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.language')),
            ],
        ),
        migrations.AddField(
            model_name='gloss',
            name='senses',
            field=models.ManyToManyField(to='dictionary.sense'),
        ),
    ]
# Generated by Django 4.2.20 on 2025-05-08 08:09

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dictionary', '0088_gloss_release_information'),
    ]

    operations = [
        migrations.AddField(
            model_name='definition',
            name='creationDate',
            field=models.DateField(null=True, verbose_name='Creation date'),
        ),
        migrations.AddField(
            model_name='definition',
            name='creator',
            field=models.ManyToManyField(to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='definition',
            name='lastUpdated',
            field=models.DateTimeField(auto_now=True, verbose_name='Last updated'),
        ),
    ]

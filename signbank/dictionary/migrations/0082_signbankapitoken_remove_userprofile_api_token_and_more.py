# Generated by Django 4.2.11 on 2024-05-02 11:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dictionary', '0081_annotatedsentence_annotatedsentencetranslation_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='SignbankAPIToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_token', models.CharField(max_length=16, verbose_name='Token')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('signbank_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='tokens', to=settings.AUTH_USER_MODEL, verbose_name='Signbank User')),
            ],
            options={
                'verbose_name': 'Token',
                'verbose_name_plural': 'Tokens',
            },
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='api_token',
        ),
        migrations.DeleteModel(
            name='SignbankToken',
        ),
    ]

# Generated by Django 4.2.10 on 2024-07-10 13:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0083_annotatedsentencesource'),
        ('video', '0010_delete_video_alter_glossvideonme_options_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='annotatedvideo',
            name='corpus',
        ),
        migrations.AddField(
            model_name='annotatedvideo',
            name='source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='dictionary.annotatedsentencesource'),
        ),
    ]

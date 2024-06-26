# Generated by Django 4.2.11 on 2024-06-06 09:39

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0082_signbankapitoken_remove_userprofile_api_token_and_more'),
        ('video', '0008_annotatedvideo_corpus'),
    ]

    operations = [
        migrations.CreateModel(
            name='GlossVideoNME',
            fields=[
                ('glossvideo_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='video.glossvideo')),
                ('offset', models.IntegerField(default=1)),
            ],
            bases=('video.glossvideo',),
        ),
        migrations.CreateModel(
            name='GlossVideoDescription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.language')),
                ('nmevideo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='video.glossvideonme')),
            ],
        ),
    ]

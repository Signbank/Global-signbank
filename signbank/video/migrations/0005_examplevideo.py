# Generated by Django 4.1.7 on 2023-05-10 12:42

from django.db import migrations, models
import django.db.models.deletion
import signbank.video.models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0068_examplesentence_sensetranslation_sense_and_more'),
        ('video', '0004_auto_20191120_0937'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExampleVideo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('videofile', models.FileField(storage=signbank.video.models.GlossVideoStorage(), upload_to=signbank.video.models.get_video_file_path, validators=[signbank.video.models.validate_file_extension], verbose_name='video file')),
                ('exampleSentence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dictionary.examplesentence')),
            ],
        ),
    ]
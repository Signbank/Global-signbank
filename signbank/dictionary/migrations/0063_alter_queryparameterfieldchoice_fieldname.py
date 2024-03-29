# Generated by Django 4.1.7 on 2023-03-27 13:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0062_alter_dataset_options_alter_gloss_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='queryparameterfieldchoice',
            name='fieldName',
            field=models.CharField(choices=[('wordClass', 'wordClass'), ('handedness', 'handedness'), ('handCh', 'handCh'), ('relatArtic', 'relatArtic'), ('locprim', 'locprim'), ('relOriMov', 'relOriMov'), ('relOriLoc', 'relOriLoc'), ('oriCh', 'oriCh'), ('contType', 'contType'), ('movSh', 'movSh'), ('movDir', 'movDir'), ('namEnt', 'namEnt'), ('valence', 'valence'), ('definitionRole', 'definitionRole')], max_length=20, verbose_name='Field Name'),
        ),
    ]

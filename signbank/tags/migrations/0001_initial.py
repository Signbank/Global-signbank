# Generated migration for custom tags app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=100, unique=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Tag',
                'verbose_name_plural': 'Tags',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='TaggedItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('content_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype')),
                ('tag', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='tags.tag')),
            ],
            options={
                'verbose_name': 'Tagged Item',
                'verbose_name_plural': 'Tagged Items',
            },
        ),
        migrations.AddIndex(
            model_name='taggeditem',
            index=models.Index(fields=['content_type', 'object_id'], name='tags_tagge_content_idx'),
        ),
        migrations.AddIndex(
            model_name='taggeditem',
            index=models.Index(fields=['tag'], name='tags_tagge_tag_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='taggeditem',
            unique_together={('tag', 'content_type', 'object_id')},
        ),
    ]

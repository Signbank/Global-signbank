from pathlib import Path
from tempfile import TemporaryDirectory

from django.core import serializers
from django.db import migrations, transaction
from django.db.models import Q


FIXTURES = (
    ('pages.json', ('pages',)),
    ('keywords.json', ('dictionary.keyword',)),
    ('languages.json', ('dictionary.language',)),
    ('fieldchoices.json', ('dictionary.fieldchoice',)),
    ('signlanguages.json', ('dictionary.signlanguage',)),
    ('handshapes.json', ('dictionary.handshape',)),
    ('datasets.json', ('dictionary.dataset',)),
    ('derivationhistorys.json', (
        'dictionary.derivationhistory', 'dictionary.derivationhistorytranslation',
    )),
    ('semanticfields.json', (
        'dictionary.semanticfield', 'dictionary.semanticfieldtranslation',
    )),
)


def clean_data(apps, alias):
    User = apps.get_model('auth', 'User')
    Site = apps.get_model('sites', 'Site')
    Keyword = apps.get_model('dictionary', 'Keyword')
    Translation = apps.get_model('dictionary', 'Translation')

    users = User.objects.using(alias).filter(
        Q(email__iendswith='@example.com') | Q(email__icontains='sharklasers')
    )
    deleted_users = users.count()
    users.delete()
    Site.objects.using(alias).filter(domain__iexact='example.com').delete()

    # Match spaces_at_end_of_keywords without importing current model classes.
    for spaces in (1, 2):
        keywords = Keyword.objects.using(alias).filter(text__endswith=' ' * spaces)
        for keyword in keywords:
            shorter = Keyword.objects.using(alias).filter(text=keyword.text[:-spaces]).first()
            if shorter is not None:
                Translation.objects.using(alias).filter(translation_id=keyword.pk).update(
                    translation_id=shorter.pk
                )
                keyword.delete(using=alias)
    print(f'\nMySQL preparation: removed {deleted_users} bogus users and cleaned sites/keywords.')


def export_data(apps, alias, directory):
    models = [
        model for model in apps.get_models()
        if model._meta.managed and not model._meta.proxy
    ]
    exported_labels = {label for _, labels in FIXTURES for label in labels}

    def matches(model, labels):
        return model._meta.app_label in labels or model._meta.label_lower in labels

    def objects(selected_models):
        for model in selected_models:
            yield from model._base_manager.using(alias).order_by(
                model._meta.pk.name
            ).iterator(chunk_size=2000)

    for filename, labels in (*FIXTURES, ('remaining_data.json', ())):
        selected = [
            model for model in models
            if (not matches(model, exported_labels) if not labels else matches(model, labels))
        ]
        with (directory / filename).open('w', encoding='utf-8') as stream:
            serializers.serialize('json', objects(selected), indent=4, stream=stream)


def prepare_mysql_export(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'sqlite':
        raise RuntimeError('MySQL preparation must run on the old SQLite database.')
    if connection.is_in_memory_db():
        print('\nSkipping MySQL export for an in-memory SQLite database.')
        return

    directory = Path(connection.settings_dict['NAME']).resolve().parent / 'mysql_export'
    if directory.exists():
        raise RuntimeError(
            f'Refusing to overwrite {directory}. Move the previous export to a safe '
            'location before retrying.'
        )

    # Publish the directory only after every fixture has been written successfully.
    with TemporaryDirectory(prefix='.mysql_export-', dir=directory.parent) as temporary:
        with transaction.atomic(using=connection.alias):
            clean_data(apps, connection.alias)
            export_data(apps, connection.alias, Path(temporary))
            Path(temporary).rename(directory)

    print(
        f'\nMySQL preparation steps 1 and 2 complete. Fixtures: {directory}\n'
        'Keep Signbank writes stopped. Set SWITCH_TO_MYSQL=True when ready to '
        'continue with the MySQL schema and import steps; these fixtures have not '
        'yet been imported.'
    )


class Migration(migrations.Migration):
    dependencies = [
        ('dictionary', '0109_alter_derivationhistory_new_id_and_more'),
        ('feedback', '0014_missingsignfeedback_sentence_and_more'),
        ('pages', '0009_remove_page_content_arabic_and_more'),
        ('video', '0016_phonologicalvariationvideo'),
        ('communication', '0001_initial'),
        ('tagging', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
        ('sites', '0002_alter_domain_unique'),
        ('sessions', '0001_initial'),
        ('admin', '0003_logentry_add_action_flag_choices'),
        ('flatpages', '0001_initial'),
        ('guardian', '__latest__'),
        ('django_summernote', '__latest__'),
    ]

    operations = [
        migrations.RunPython(prepare_mysql_export),
    ]

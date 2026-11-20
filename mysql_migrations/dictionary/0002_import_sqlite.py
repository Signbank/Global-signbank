"""Import the export from SQLite migration 0110 after all MySQL tables exist.

Stop writes and back up SQLite before exporting. Set SWITCH_TO_MYSQL=True,
configure the MySQL connection and MYSQL_EXPORT_DIRECTORY, then run migrate.
The export is retained for recovery; this data migration is irreversible.
"""

from collections import Counter
from pathlib import Path

from django.conf import settings
from django.core.management.color import no_style
from django.core.serializers.base import DeserializationError
from django.core.serializers.json import Deserializer
from django.db import migrations, transaction


FIXTURES = (
    'languages.json',
    'pages.json',
    'keywords.json',
    'signlanguages.json',
    'fieldchoices.json',
    'handshapes.json',
    'derivationhistorys.json',
    'semanticfields.json',
    'datasets.json',
    'remaining_data.json',
)

BOOTSTRAP_MODELS = (
    'dictionary.userprofile',
    'auth.permission',
    'auth.group',
    'auth.user',
    'contenttypes.contenttype',
    'sites.site',
)


def import_fixtures(apps, connection, directory):
    missing = [name for name in FIXTURES if not (directory / name).is_file()]
    if missing:
        raise RuntimeError(
            f'MySQL import requires the complete SQLite export in {directory}. '
            f'Missing: {", ".join(missing)}. Run SQLite migration 0110 first, '
            'or correct MYSQL_EXPORT_DIRECTORY.'
        )

    class HistoricalDeserializer(Deserializer):
        @staticmethod
        def _get_model_from_node(identifier):
            try:
                return apps.get_model(identifier)
            except (LookupError, ValueError) as error:
                raise DeserializationError(f'Unknown exported model: {identifier}') from error

    models = [
        model for model in apps.get_models()
        if model._meta.managed and not model._meta.proxy
    ]
    all_models = [
        model for model in apps.get_models(include_auto_created=True)
        if model._meta.managed and not model._meta.proxy
    ]
    alias = connection.alias
    counts = Counter()
    with connection.constraint_checks_disabled(), transaction.atomic(using=alias):
        for model in all_models:
            if model._meta.label_lower not in BOOTSTRAP_MODELS:
                if model._base_manager.using(alias).exists():
                    raise RuntimeError(
                        f'Refusing to import into populated table {model._meta.db_table}. '
                        'Use a fresh MySQL database; existing application data is not overwritten.'
                    )

        for label in BOOTSTRAP_MODELS:
            apps.get_model(label)._base_manager.using(alias).all().delete()

        for filename in FIXTURES:
            with (directory / filename).open(encoding='utf-8') as stream:
                for item in HistoricalDeserializer(stream, using=alias):
                    item.save(using=alias)
                    counts[item.object._meta.label_lower] += 1

        # MySQL does not check existing rows when FOREIGN_KEY_CHECKS is re-enabled.
        connection.check_constraints(
            table_names=[model._meta.db_table for model in all_models]
        )
        for model in models:
            expected = counts[model._meta.label_lower]
            actual = model._base_manager.using(alias).count()
            if actual != expected:
                raise RuntimeError(
                    f'Import count mismatch for {model._meta.label}: '
                    f'expected {expected}, found {actual}.'
                )
        with connection.cursor() as cursor:
            for sql in connection.ops.sequence_reset_sql(no_style(), models):
                cursor.execute(sql)
    return sum(counts.values())


def import_mysql_data(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != 'mysql':
        raise RuntimeError('The MySQL import migration requires a MySQL database.')

    directory = Path(settings.MYSQL_EXPORT_DIRECTORY)
    # Rollback on import failure is only reliable with transactional tables.
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT TABLE_NAME, ENGINE FROM information_schema.TABLES '
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
        )
        tables = {
            model._meta.db_table for model in apps.get_models(include_auto_created=True)
            if model._meta.managed and not model._meta.proxy
        }
        tables.add('django_migrations')
        non_transactional = [
            name for name, engine in cursor.fetchall()
            if name in tables and engine != 'InnoDB'
        ]
        if non_transactional:
            raise RuntimeError(
                'MySQL import requires InnoDB tables for rollback: '
                + ', '.join(non_transactional)
            )
        cursor.execute('SELECT @@SESSION.sql_mode')
        original_sql_mode = cursor.fetchone()[0]
        modes = set(original_sql_mode.split(',')) - {''}
        modes.update(('NO_AUTO_VALUE_ON_ZERO', 'STRICT_TRANS_TABLES'))
        cursor.execute('SET SESSION sql_mode = %s', [','.join(sorted(modes))])

    try:
        count = import_fixtures(apps, connection, directory)
    finally:
        with connection.cursor() as cursor:
            cursor.execute('SET SESSION sql_mode = %s', [original_sql_mode])

    print(
        f'\nMySQL migration complete: imported and validated {count} objects '
        f'from {directory}. Foreign-key checks are enabled. '
        'The SQLite database and exported fixtures have been retained.'
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('dictionary', '0001_initial'),
        ('feedback', '0001_initial'),
        ('pages', '0001_initial'),
        ('video', '0001_initial'),
        ('tagging', '0001_initial'),
        ('communication', '0001_initial'),
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
        migrations.RunPython(import_mysql_data, atomic=False),
    ]

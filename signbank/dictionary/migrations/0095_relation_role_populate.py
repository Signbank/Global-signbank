# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from signbank.settings.server_specific import MODELTRANSLATION_LANGUAGES

# set up predefined machine values for constant Relation Role Choices
RELATION_ROLE_CHOICES = [('homonym', 2, 'Homonym'),
                         ('synonym', 3, 'Synonym'),
                         ('variant', 4, 'Variant'),
                         ('antonym', 5, 'Antonym'),
                         ('hyponym', 6, 'Hyponym'),
                         ('hypernym', 7, 'Hypernym'),
                         ('seealso', 8, 'See Also'),
                         ('paradigm', 9, 'Handshape Paradigm')
                         ]

def add_default_relation_roles(apps, schema_editor):
    """
    Add 0 and 1 choices to RelationRole FieldChoice category
    :param apps:
    :param schema_editor:
    :return:
    """
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    new_field_choice_0, created = FieldChoice.objects.get_or_create(field='RelationRole', machine_value=0)
    new_field_choice_1, created = FieldChoice.objects.get_or_create(field='RelationRole', machine_value=1)
    for language in MODELTRANSLATION_LANGUAGES:
        field_name = 'name_' + language.replace('-', '_')
        setattr(new_field_choice_0, field_name, '-')
        setattr(new_field_choice_1, field_name, 'N/A')
    new_field_choice_0.save()
    new_field_choice_1.save()

def add_constant_relation_roles(apps, schema_editor):
    """
    Add predefined choices to RelationRole FieldChoice category
    :param apps:
    :param schema_editor:
    :return:
    """
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    for (role, machine_value, verbose_name) in RELATION_ROLE_CHOICES:
        new_field_choice, created = FieldChoice.objects.get_or_create(field='RelationRole', machine_value=machine_value)
        for language in MODELTRANSLATION_LANGUAGES:
            field_name = 'name_' + language.replace('-', '_')
            setattr(new_field_choice, field_name, verbose_name)
        new_field_choice.save()

def copy_relation_role_values(apps, schema_editor):
    FieldChoice = apps.get_model('dictionary', 'FieldChoice')
    Relation = apps.get_model('dictionary', 'Relation')

    # Put all relation role field choices in a dict for convenient lookup
    relation_roles = dict([(relation_role.machine_value, relation_role) for relation_role in FieldChoice.objects.filter(field='RelationRole')])
    role_to_machine_value = dict([(role, machine_value) for (role, machine_value, verbose_name) in RELATION_ROLE_CHOICES])

    # Copy the field choice objects for the role values for each Relation
    for relation in Relation.objects.all():
        if relation.role not in role_to_machine_value.keys():
            relation.role_fk = FieldChoice.objects.get(field='RelationRole', machine_value=0)
        relation.role_fk = relation_roles[role_to_machine_value[relation.role]]
        relation.save()

class Migration(migrations.Migration):

    dependencies = [
        ('dictionary', '0095_relation_role_fk_alter_fieldchoice_field'),
    ]

    operations = [
        migrations.RunPython(add_default_relation_roles),
        migrations.RunPython(add_constant_relation_roles),
        migrations.RunPython(copy_relation_role_values),
    ]

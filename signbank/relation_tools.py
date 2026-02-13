from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.utils.translation import gettext, gettext_lazy as _

from signbank.dictionary.models import (Gloss, Relation, FieldChoice)

def ensure_synonym_transitivity(gloss):
    assert isinstance(gloss, Gloss), "Not a Gloss object."

    try:
        synonym = FieldChoice.objects.get(field='RelationRole', name__iexact="Synonym")
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        raise ValueError(_("FieldChoice for Synonym is not defined."))

    relations_source = Relation.objects.filter(source=gloss)
    relations_target = Relation.objects.filter(target=gloss)
    synonym_relations_using_sources = relations_source.filter(target__archived__exact=False, role_fk=synonym)
    synonym_relations_using_targets = relations_target.filter(source__archived__exact=False, role_fk=synonym)

    # first do direct synonyms
    other_glosses_in_synonym_with_this_gloss = []
    for rel in synonym_relations_using_sources:
        if rel.target in other_glosses_in_synonym_with_this_gloss:
            continue
        other_glosses_in_synonym_with_this_gloss.append(rel.target)
    for rel in synonym_relations_using_targets:
        if rel.source in other_glosses_in_synonym_with_this_gloss:
            continue
        other_glosses_in_synonym_with_this_gloss.append(rel.source)

    # for direct synonyms, make sure relations are symmetric
    for new_synonym_object in other_glosses_in_synonym_with_this_gloss:
        if new_synonym_object == gloss:
            continue
        rel, created = Relation.objects.get_or_create(source=gloss, target=new_synonym_object, role_fk=synonym)
        rel.save()
        revrel, created = Relation.objects.get_or_create(source=new_synonym_object, target=gloss, role_fk=synonym)
        revrel.save()

    # the other glosses found above are all in symmetric synonym relations with this gloss
    # now do transitive synonyms
    transitive_synonym_glosses = []
    for other_gloss in other_glosses_in_synonym_with_this_gloss:
        transitive_synonym = other_gloss.get_synonyms()
        for transitive_gloss in transitive_synonym:
            if transitive_gloss in transitive_synonym_glosses or transitive_gloss == gloss:
                continue
            transitive_synonym_glosses.append(transitive_gloss)

    # save these transitive synonyms as synonyms of this gloss, if necessary
    for new_synonym_object in transitive_synonym_glosses:
        if new_synonym_object == gloss:
            continue
        rel, created = Relation.objects.get_or_create(source=gloss, target=new_synonym_object, role_fk=synonym)
        rel.save()
        revrel, created = Relation.objects.get_or_create(source=new_synonym_object, target=gloss, role_fk=synonym)
        revrel.save()

def remove_transitive_synonym(rel):
    assert isinstance(rel, Relation), "Not a Relation object."

    try:
        synonym = FieldChoice.objects.get(field='RelationRole', name__iexact="Synonym")
    except (ObjectDoesNotExist, MultipleObjectsReturned):
        raise ValueError(_("FieldChoice for Synonym is not defined."))

    transitive_synonyms = rel.target.get_synonyms()
    trans_relations = []
    for trans_gloss in transitive_synonyms:
        relations_source = Relation.objects.filter(source=trans_gloss)
        relations_target = Relation.objects.filter(target=trans_gloss)
        trans_gloss_target_synonym = relations_source.filter(role_fk=synonym)
        trans_gloss_source_synonym = relations_target.filter(role_fk=synonym)
        for trans_rel in trans_gloss_target_synonym:
            if trans_rel.target in trans_relations:
                continue
            if trans_rel.target != rel.target:
                continue
            trans_relations.append(trans_rel)
        for trans_rel in trans_gloss_source_synonym:
            if trans_rel.source in trans_relations:
                continue
            if trans_rel.source != rel.target:
                continue
            trans_relations.append(trans_rel)

    for synonym_relation in trans_relations:
        synonym_relation.delete()
    rel.delete()

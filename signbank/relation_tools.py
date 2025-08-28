

from signbank.dictionary.models import (Gloss, Relation)

def ensure_synonym_transitivity(gloss):
    assert isinstance(gloss, Gloss), TypeError("Not a Gloss object.")

    synonym_relations_using_sources = gloss.relation_sources.all().filter(target__archived__exact=False,
                                                                          source__archived__exact=False, role='synonym')
    synonym_relations_using_targets = gloss.relation_targets.all().filter(target__archived__exact=False,
                                                                          source__archived__exact=False, role='synonym')

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
        rel, created = Relation.objects.get_or_create(source=gloss, target=new_synonym_object, role='synonym')
        rel.save()
        revrel, created = Relation.objects.get_or_create(source=new_synonym_object, target=gloss, role='synonym')
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
        rel, created = Relation.objects.get_or_create(source=gloss, target=new_synonym_object, role='synonym')
        rel.save()
        revrel, created = Relation.objects.get_or_create(source=new_synonym_object, target=gloss, role='synonym')
        revrel.save()

def remove_transitive_synonym(rel):
    assert isinstance(rel, Relation), TypeError("Not a Relation object.")

    transitive_synonyms = rel.target.get_synonyms()
    trans_relations = []
    for trans_gloss in transitive_synonyms:
        trans_gloss_target_synonym = trans_gloss.relation_sources.all().filter(role='synonym')
        trans_gloss_source_synonym = trans_gloss.relation_targets.all().filter(role='synonym')
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

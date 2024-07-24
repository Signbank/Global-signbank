from signbank.dictionary.models import *
from signbank.tools import get_default_annotationidglosstranslation
from django.utils.translation import override, gettext_lazy as _, activate


def morpheme_is_related_to(morpheme, interface_language_code, default_language_code):
    """
    This function is used in the Delete Morpheme modal of the MorphemeDetailView template
    It yields a dictionary of different kinds of related objects to the morpheme.
    Because it is used in the template, it computes display appropriate data
    """
    related_objects = dict()

    # Get the set of all the Gloss signs that point to morpheme
    other_glosses_that_point_to_morpheme = SimultaneousMorphologyDefinition.objects.filter(
        morpheme_id__exact=morpheme.id)
    appears_in = []
    for sim_morph in other_glosses_that_point_to_morpheme:
        parent_gloss = sim_morph.parent_gloss
        translated_word_class = parent_gloss.wordClass.name if parent_gloss.wordClass else '-'
        appears_in.append((parent_gloss, translated_word_class))

    appears_in_glosses = []
    for parent_gloss, translated_word_class in appears_in:
        sign_display = str(parent_gloss.id)
        morph_texts = parent_gloss.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        appears_in_glosses.append(sign_display)
    simultaneous = ', '.join(appears_in_glosses)
    if simultaneous:
        related_objects[_('Simultaneous Morphology')] = simultaneous

    return related_objects


def morpheme_related_objects(morpheme):

    related_objects = []
    # Make a list of all the glosses that point to this morpheme
    other_glosses_that_point_to_morpheme = SimultaneousMorphologyDefinition.objects.filter(
        morpheme_id__exact=morpheme.id)
    for sim_morph in other_glosses_that_point_to_morpheme:
        related_objects.append(sim_morph.parent_gloss)

    return related_objects


def gloss_is_related_to(gloss, interface_language_code, default_language_code):
    """
    This function is used in the Delete Sign modal of the GlossDetailView template
    It yields a dictionary of different kinds of related objects to the gloss.
    Because it is used in the template, it computes display appropriate data
    """
    related_objects = dict()
    related_glosses = [(relation.role, relation.target)
                       for relation in Relation.objects.filter(source=gloss).exclude(target=gloss)]
    relglosses = []
    for relrole, relgloss in related_glosses:
        sign_display = str(relgloss.id)
        morph_texts = relgloss.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        relglosses.append(relrole.upper() + ': ' + sign_display)
    related_glosses = ', '.join(relglosses)
    if related_glosses:
        related_objects[_('Relations')] = related_glosses

    # the morpheme field of MorphologyDefinition is a ForeignKey to Gloss
    morphdefs = []
    for morphdef in gloss.parent_glosses.filter(parent_gloss__archived__exact=False,
                                                morpheme__archived__exact=False):
        translated_role = morphdef.role.name
        sign_display = str(morphdef.morpheme.id)
        morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        morphdefs.append((translated_role, sign_display))
    morphdefs = sorted(morphdefs, key=lambda tup: tup[0])  # sort by translated_role
    morphemes = ' + '.join([sign_display for (translated_role, sign_display) in morphdefs])
    if morphemes:
        related_objects[_('Sequential Morphology')] = morphemes

    appears_in = [morpheme.parent_gloss
                  for morpheme in MorphologyDefinition.objects.filter(morpheme=gloss)]

    appears_in_glosses = []
    for compound in appears_in:
        sign_display = str(compound.id)
        morph_texts = compound.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        appears_in_glosses.append(sign_display)
    compounds = ', '.join(appears_in_glosses)
    if compounds:
        related_objects[_('Appears in Compound')] = compounds

    # the morpheme field of SimultaneousMorphologyDefinition is a ForeignKey to Morpheme
    simultaneous = [simdef.morpheme
                    for simdef in SimultaneousMorphologyDefinition.objects.filter(parent_gloss=gloss)]
    simglosses = []
    for simgl in simultaneous:
        sign_display = str(simgl.id)
        morph_texts = simgl.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        simglosses.append(sign_display)
    simultaneous = ', '.join(simglosses)
    if simultaneous:
        related_objects[_('Simultaneous Morphology')] = simultaneous

    # the glosses field of SimultaneousMorphologyDefinition is a ForeignKey to Gloss
    blends = [blendmorph.glosses
              for blendmorph in BlendMorphology.objects.filter(parent_gloss=gloss)]
    blendglosses = []
    for blendgloss in blends:
        sign_display = str(blendgloss.id)
        morph_texts = blendgloss.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        blendglosses.append(sign_display)
    blends = ', '.join(blendglosses)
    if blends:
        related_objects[_('Blend Morphology')] = blends

    partofblends = [blendmorph.parent_gloss
                    for blendmorph in BlendMorphology.objects.filter(glosses=gloss)]
    blendglosses = []
    for blendgloss in partofblends:
        sign_display = str(blendgloss.id)
        morph_texts = blendgloss.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language_code in morph_texts.keys():
                sign_display = morph_texts[interface_language_code]
            else:
                sign_display = morph_texts[default_language_code]
        blendglosses.append(sign_display)
    appearasinblends = ', '.join(blendglosses)
    if appearasinblends:
        related_objects[_('Part of Blend')] = appearasinblends

    return related_objects


def glosses_in_lemma_group(gloss):

    lemma_group = [gl for gl in Gloss.objects.filter(lemma=gloss.lemma).exclude(id=gloss.id)]

    return lemma_group


def gloss_related_objects(gloss):

    related_glosses_target = [relation.target
                              for relation in Relation.objects.filter(source=gloss)]

    related_glosses_source = [relation.source
                              for relation in Relation.objects.filter(target=gloss)]

    # the morpheme field of MorphologyDefinition is a ForeignKey to Gloss
    morphemes = [morpheme.morpheme
                 for morpheme in MorphologyDefinition.objects.filter(parent_gloss=gloss)]

    appears_in = [morpheme.parent_gloss
                  for morpheme in MorphologyDefinition.objects.filter(morpheme=gloss)]

    siblings = []
    for compound in appears_in:
        compound_glosses = [morpheme.morpheme
                            for morpheme in MorphologyDefinition.objects.filter(parent_gloss=compound)]
        for gl in compound_glosses:
            if gl != gloss and gl not in siblings:
                siblings.append(gl)

    # the morpheme field of SimultaneousMorphologyDefinition is a ForeignKey to Morpheme
    simultaneous = [simdef.morpheme
                    for simdef in SimultaneousMorphologyDefinition.objects.filter(parent_gloss=gloss)]

    # the glosses field of SimultaneousMorphologyDefinition is a ForeignKey to Gloss
    blends = [blendmorph.glosses
              for blendmorph in BlendMorphology.objects.filter(parent_gloss=gloss)]

    partofblends = [blendmorph.parent_gloss
                    for blendmorph in BlendMorphology.objects.filter(glosses=gloss)]

    blendsiblings = []
    for compound in partofblends:
        blendsiblings.append(compound)
        compound_glosses = [morpheme.glosses
                            for morpheme in BlendMorphology.objects.filter(parent_gloss=compound)]
        for gl in compound_glosses:
            if gl != gloss and gl not in blendsiblings:
                blendsiblings.append(gl)

    related_gloss_unique = list(set(related_glosses_target + related_glosses_source + morphemes + appears_in
                                    + siblings + simultaneous + blends + blendsiblings))
    return related_gloss_unique


def transitive_related_objects(gloss):
    related_objects = gloss_related_objects(gloss)
    # transitive related objects for other glosses in lemma group
    lemma_group = glosses_in_lemma_group(gloss)
    # the glosses and the ids are both maintained
    extended_related_objects = []
    extended_related_objects_ids = []
    for ro in related_objects:
        if ro.id not in extended_related_objects_ids:
            extended_related_objects_ids.append(ro.id)
            extended_related_objects.append(ro)
        related_related = gloss_related_objects(ro)
        for rr in related_related:
            if rr.id not in extended_related_objects_ids:
                extended_related_objects.append(rr)
                extended_related_objects_ids.append(rr.id)
    for lgg in lemma_group:
        lgg_related_objects = gloss_related_objects(lgg)
        for lggro in lgg_related_objects:
            if lggro.id not in extended_related_objects_ids:
                extended_related_objects.append(lggro)
                extended_related_objects_ids.append(lggro.id)
    return extended_related_objects


def same_translation_languages(dataset1, dataset2):
    if dataset1 == dataset2:
        return True
    source_translation_languages = [ds.id for ds in dataset1.translation_languages.all()]
    target_translation_languages = [ds.id for ds in dataset2.translation_languages.all()]
    return source_translation_languages == target_translation_languages


def gloss_exists_in_dataset(gloss, dataset):

    if gloss.lemma.dataset == dataset:
        # this method should not be called in this case
        # False is returned because there is no conflict
        return False, []
    gloss_exists = False
    lemma_exists = False
    text_overlap = []
    gloss_lemma_translations = gloss.lemma.lemmaidglosstranslation_set.all()
    gloss_annotation_translations = gloss.annotationidglosstranslation_set.all()
    for lemma_translation in gloss_lemma_translations:
        lemmas_with_same_text = dataset.lemmaidgloss_set.filter(lemmaidglosstranslation__text__exact=lemma_translation.text,
                                                                lemmaidglosstranslation__language=lemma_translation.language)
        if lemmas_with_same_text.count():
            # The lemma translation text is already in use in the dataset
            lemma_exists = True
    target_dataset_glosses = Gloss.objects.filter(lemma__dataset=dataset)
    for gloss_translation in gloss_annotation_translations:
        glosses_with_same_text = target_dataset_glosses.filter(annotationidglosstranslation__text__exact=gloss_translation.text,
                                                               annotationidglosstranslation__language=gloss_translation.language)
        if glosses_with_same_text.count():
            # The gloss annotation text is already in use in the dataset
            gloss_exists = True
    if lemma_exists:
        text_overlap.append("Lemma "+gloss.idgloss)
    if gloss_exists:
        text_overlap.append("Gloss "+get_default_annotationidglosstranslation(gloss))

    return lemma_exists or gloss_exists, text_overlap


def okay_to_move_gloss(gloss, dataset_target):

    if not same_translation_languages(gloss.lemma.dataset, dataset_target):
        return False, []

    gloss_exists, text_overlap = gloss_exists_in_dataset(gloss, dataset_target)

    return not gloss_exists, text_overlap


def okay_to_move_glosses(glosses, dataset_target):

    okay_to_move = True
    text_overlap = []
    for gloss in glosses:
        gloss_exists, feedback = gloss_exists_in_dataset(gloss, dataset_target)

        okay_to_move &= not gloss_exists
        text_overlap += feedback

    return okay_to_move, text_overlap

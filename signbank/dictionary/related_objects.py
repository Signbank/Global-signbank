from signbank.dictionary.models import *
from django.utils.translation import override, gettext_lazy as _, activate


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
    for morphdef in gloss.parent_glosses.all():
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


def gloss_related_objects(gloss):

    related_glosses = [relation.target
                       for relation in Relation.objects.filter(source=gloss).exclude(target=gloss)]

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

    related_gloss_unique = list(set(related_glosses + morphemes + appears_in
                                    + siblings + simultaneous + blends + blendsiblings))
    return related_gloss_unique


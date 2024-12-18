from django.db.models import F, ExpressionWrapper, Count
from django.db.models import OuterRef, Subquery
from django.db.models.query import QuerySet
from django.db.models.functions import Concat
from django.db.models import Q, IntegerField, CharField, TextField, Value as V
from signbank.dictionary.models import *
from signbank.video.models import GlossVideoDescription, GlossVideo, GlossVideoNME


def get_annotation_idgloss_per_language_dict(gloss):
    default_language = gloss.lemma.dataset.default_language
    gloss_annotations = gloss.annotationidglosstranslation_set.all()
    default_annotationidglosstranslation = gloss.annotationidglosstranslation_set.filter(language=default_language).first()
    if default_annotationidglosstranslation:
        gloss_default_annotationidglosstranslation = default_annotationidglosstranslation.text
    elif not gloss_annotations:
        gloss_default_annotationidglosstranslation = str(gloss.id)
    else:
        gloss_default_annotationidglosstranslation = gloss_annotations.first().text

    annotation_idgloss_per_language = dict()
    for language in gloss.dataset.translation_languages.all():
        try:
            annotation_text = gloss.annotationidglosstranslation_set.get(language=language).text
        except ObjectDoesNotExist:
            annotation_text = gloss_default_annotationidglosstranslation
        annotation_idgloss_per_language[language] = annotation_text
    return annotation_idgloss_per_language


def get_simultaneous_morphology(gloss, interface_language):
    default_language = gloss.lemma.dataset.default_language
    dataset_languages = gloss.lemma.dataset.translation_languages.all()
    simultaneous_morphology = []
    for sim_morph in gloss.simultaneous_morphology.filter(parent_gloss__archived__exact=False):
        translated_morph_type = sim_morph.morpheme.mrpType.name if sim_morph.morpheme.mrpType else ''
        morpheme_annotation_idgloss = {}
        for language in dataset_languages:
            morpheme_annotation_idgloss[
                language.language_code_2char] = sim_morph.morpheme.annotationidglosstranslation_set.filter(
                language=language).first()
        if interface_language in dataset_languages:
            default_annotation = morpheme_annotation_idgloss[interface_language.language_code_2char]
        else:
            default_annotation = morpheme_annotation_idgloss[default_language.language_code_2char]
        morpheme_display = default_annotation.text if default_annotation else str(sim_morph.id)

        simultaneous_morphology.append((sim_morph, morpheme_display, translated_morph_type))
    return simultaneous_morphology


def get_sequential_morphology(gloss, interface_language):
    default_language = gloss.lemma.dataset.default_language
    morphdefs = []
    for morphdef in gloss.parent_glosses.filter(parent_gloss__archived__exact=False,
                                                morpheme__archived__exact=False):

        translated_role = morphdef.role.name if morphdef.role else ''

        sign_display = str(morphdef.morpheme.id)
        morph_texts = morphdef.morpheme.get_annotationidglosstranslation_texts()
        if morph_texts.keys():
            if interface_language.language_code_2char in morph_texts.keys():
                sign_display = morph_texts[interface_language.language_code_2char]
            else:
                sign_display = morph_texts[default_language.language_code_2char]

        morphdefs.append((morphdef, translated_role, sign_display))
    return sorted(morphdefs, key=lambda tup: tup[1])


def get_other_relations(gloss):
    otherrelations = []
    for oth_rel in gloss.relation_sources.filter(target__archived__exact=False,
                                                 source__archived__exact=False):
        otherrelations.append((oth_rel, oth_rel.get_target_display()))
    return otherrelations


def get_annotated_sentences(gloss):
    annotated_sentences_1 = AnnotatedSentence.objects.filter(annotated_glosses__gloss=gloss,
                                                             annotated_glosses__isRepresentative=True).distinct().annotate(
        is_representative=V(1, output_field=IntegerField()))
    annotated_sentences_2 = AnnotatedSentence.objects.filter(annotated_glosses__gloss=gloss,
                                                             annotated_glosses__isRepresentative=False).distinct().annotate(
        is_representative=V(0, output_field=IntegerField()))
    annotated_sentences = annotated_sentences_1.union(annotated_sentences_2).order_by('-is_representative')
    annotated_sentences_with_video = []
    for annotated_sentence in annotated_sentences:
        video_path = annotated_sentence.get_video_path()
        if video_path and annotated_sentence not in annotated_sentences_with_video:
            annotated_sentences_with_video.append(annotated_sentence)
    annotated_sentences = annotated_sentences_with_video
    if len(annotated_sentences) <= 3:
        return annotated_sentences
    else:
        return annotated_sentences[0:3]


def get_nme_video_descriptions(gloss):
    glossnmevideos = GlossVideoNME.objects.filter(gloss=gloss)
    nme_video_descriptions = dict()
    for nmevideo in glossnmevideos:
        nme_video_descriptions[nmevideo] = {}
        for language in gloss.dataset.translation_languages.all():
            try:
                description_text = GlossVideoDescription.objects.get(nmevideo=nmevideo, language=language).text
            except ObjectDoesNotExist:
                description_text = ""
            nme_video_descriptions[nmevideo][language] = description_text
    return nme_video_descriptions


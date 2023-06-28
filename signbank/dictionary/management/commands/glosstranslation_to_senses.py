from signbank.dictionary.models import *
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = 'make senses from gloss translations.'

    def add_arguments(self, parser):
        parser.add_argument('dataset_acronym', type=str)

    def handle(self, *args, **options):
        dataset = Dataset.objects.get(acronym=options['dataset_acronym'])
        
        for gloss in Gloss.objects.filter(lemma__dataset = dataset):
            non_empty_translations = gloss.translation_set.all().exclude(translation__text='')
            if not non_empty_translations:
                continue
            
            # Add translations in each language to a dictionary
            vals = {}
            for dataset_language in dataset.translation_languages.all():
                translations = []
                for translation in gloss.translation_set.filter(language=dataset_language).order_by('translation__index'):
                    if translation.translation != "":
                        translations.append(translation.translation.text.strip())
                translations = (', ').join(sorted(translations))
                if translations != '':
                    vals[str(dataset_language)] = translations

            # If no translations found, don't make a sense
            if vals == {}:
                continue

            # Check if this sense already exists
            existing_senses = []
            for existing_gloss in Gloss.objects.filter(lemma__dataset=dataset):
                existing_senses.extend(existing_gloss.senses.all())
            for existing_sense in existing_senses:
                if existing_sense.get_sense_translations_dict_without() == vals and existing_sense not in gloss.senses.all():
                    GlossSense.objects.create(gloss=gloss, sense=existing_sense, order=gloss.senses.count()+1)
                    break

            # Make a new sense object
            sense = Sense.objects.create()
            GlossSense.objects.create(gloss=gloss, sense=sense, order=gloss.senses.count()+1)

            # Add or remove keywords to the sense translations
            for dataset_language in dataset.translation_languages.all():

                if str(dataset_language) in vals:

                    for st in SenseTranslation.objects.filter(language = dataset_language):
                        if st.get_translations() == vals[str(dataset_language)]:
                            sense.senseTranslations.add(st)
                            break

                    if not sense.senseTranslations.filter(language = dataset_language).exists():
                        sensetranslation = SenseTranslation.objects.create(language = dataset_language)
                        sense.senseTranslations.add(sensetranslation)
                        for kw in sorted(list(dict.fromkeys(vals[str(sensetranslation.language)].split(", ")))):
                            keyword = Keyword.objects.get_or_create(text = kw)[0]
                            translation = None
                            try:
                                translation = Translation.objects.filter(translation = keyword, language = dataset_language)[0]
                            except:
                                translation = Translation.objects.create(translation = keyword, language = dataset_language, gloss = gloss)
                            sensetranslation.translations.add(translation)

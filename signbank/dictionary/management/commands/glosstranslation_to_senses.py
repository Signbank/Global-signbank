from signbank.dictionary.models import *
from django.core.management import BaseCommand

class Command(BaseCommand):
    help = 'make senses from gloss translations.'

    def add_arguments(self, parser):
        parser.add_argument('dataset_acronym', type=str)

    def handle(self, *args, **options):
        dataset = Dataset.objects.get(acronym=options['dataset_acronym'])
        
        for lemma in LemmaIdgloss.objects.filter(dataset = dataset):
            for gloss in Gloss.objects.filter(lemma = lemma):
                vals = {}
                for dataset_language in dataset.translation_languages.all():
                    values = []
                    for translation in gloss.translation_set.filter(language=dataset_language).order_by('translation__index'):
                        if translation.translation != "":
                            values.append(translation.translation.text.strip())
                    values = (', ').join(sorted(values))
                    if values != '':
                        vals[str(dataset_language)] = values

                # If no translations found, don't make a sense
                if vals == {}:
                    continue

                # Check if this sense already exists
                senses = Sense.objects.filter(dataset=dataset)
                gloss = Gloss.objects.all().get(id = gloss.id)
                for sense in senses:
                    if sense.get_sense_translations_dict_without() == vals:
                        if sense not in gloss.senses.all():
                            gloss.senses.add(sense)
                            break
                
                if gloss.senses.count()<1:
                    # Make a new sense object
                    sense = Sense.objects.create(dataset = dataset)
                    sense.save()
                    gloss.senses.add(sense)

                    # Add or remove keywords to the sense translations
                    for dataset_language in dataset.translation_languages.all():
                        if str(dataset_language) in vals:
                            
                            existed = False
                            for st in SenseTranslation.objects.filter(language = dataset_language):
                                if st.get_translations() == vals[str(dataset_language)]:
                                    sense.senseTranslations.add(st)
                                    existed = True

                            if not existed:
                                sensetranslation = SenseTranslation.objects.create(language = dataset_language)
                                sensetranslation.save()
                                sense.senseTranslations.add(sensetranslation)
                                for kw in sorted(list(dict.fromkeys(vals[str(sensetranslation.language)].split(", ")))):
                                    keyword = Keyword.objects.get_or_create(text = kw)[0]
                                    translation = None
                                    try:
                                        translation = Translation.objects.filter(translation = keyword, language = dataset_language)[0]
                                    except:
                                        translation = Translation.objects.create(translation = keyword, language = dataset_language, gloss = gloss)
                                    sensetranslation.translations.add(translation)

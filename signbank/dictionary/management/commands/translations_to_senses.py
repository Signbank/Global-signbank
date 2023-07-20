from django.core.exceptions import ObjectDoesNotExist

from signbank.dictionary.models import Dataset, Gloss, GlossSense, Sense, SenseTranslation
from django.core.management import BaseCommand

# for the dataset parameters, this command migrates the data
# from Translation to GlossSense, Sense, SenseTranslation


class Command(BaseCommand):
    help = 'make senses from gloss translations.'

    def add_arguments(self, parser):
        parser.add_argument('dataset_acronym', nargs="*", type=str)
        parser.add_argument(
            "--all",
            action="store_true",
            help="Process all datasets",
        )

    def handle(self, *args, **options):
        if options["all"]:
            dataset_acronyms = list(Dataset.objects.values_list('acronym', flat=True))
        elif options['dataset_acronym']:
            dataset_acronyms = options['dataset_acronym']
        else:
            print("No datasets given (or --all)")
            return

        for dataset_acronym in dataset_acronyms:
            print("Processing", dataset_acronym)
            try:
                dataset = Dataset.objects.get(acronym=dataset_acronym)
            except ObjectDoesNotExist as e:
                print("Dataset '{}' not found.".format(dataset_acronym), e)
                continue

            # see if there are already senses
            senses_for_dataset = GlossSense.objects.filter(gloss__lemma__dataset=dataset).count()
            if senses_for_dataset:
                print('Translations already mapped to senses for dataset ', dataset_acronym)
                continue

            # the gloss keywords are stored in Translation objects
            # the Translation objects refer to the gloss, a Keyword object,
            # a Language (one of the Languages of the Dataset the gloss is in)
            # contain an index field (the order in which the user arranged them in the Keywords)
            # an orderIndex field (this is the Sense Number the translation/keyword is in
            # it is possible to specify this using the Keywords Mapping page
            for gloss in Gloss.objects.filter(lemma__dataset=dataset):
                # ideally the command delete_empty_translations should be applied before this command
                non_empty_translations = gloss.translation_set.all().exclude(translation__text='')
                if not non_empty_translations:
                    # if there are no non-empty translations for this gloss, do not create anything
                    continue

                # get all the translation keywords for this gloss (languages are mixed)
                # omit the empty ones in case they have not been deleted (command delete_empty_translations)
                gloss_translations = non_empty_translations.order_by('orderIndex', 'index')

                # determine the sense numbers already specified, make them unique in orderIndices list
                orderIndices = sorted(list(set([gti.orderIndex for gti in gloss_translations])))

                # for each orderIndex, create a Sense for the gloss
                for sense_number, orderIndex in enumerate(orderIndices, 1):
                    sense_for_gloss = Sense()
                    sense_for_gloss.save()
                    glosssense = GlossSense(gloss=gloss, sense=sense_for_gloss, order=sense_number)
                    glosssense.save()

                    # create a lookup table to store SenseTranslation objects for each language of the dataset
                    # these are empty to start and not connected to the gloss yet
                    translation_lookup = dict()
                    index_per_language = dict()
                    for dataset_language in dataset.translation_languages.all():
                        index_per_language[dataset_language] = 1
                        glosssenselanguage = SenseTranslation(language=dataset_language)
                        glosssenselanguage.save()
                        translation_lookup[dataset_language] = glosssenselanguage

                    # obtain the translations of this gloss for this orderIndex
                    gloss_translations_order = gloss_translations.filter(orderIndex=orderIndex).order_by('index')
                    for gto in gloss_translations_order:
                        # the index will keep them sorted the same as they were as keywords
                        gto.index = index_per_language[gto.language]
                        gto.save()
                        # add the translation to the SenseTranslation for its language
                        translation_lookup[gto.language].translations.add(gto)
                        index_per_language[gto.language] += 1

                    # add the SenseTranslation objects to the Sense of the gloss
                    # because the set of translation languages varies for each dataset
                    # these are kept in a ManyToMany relation field of the Sense
                    for dataset_language in dataset.translation_languages.all():
                        sense_for_gloss.senseTranslations.add(translation_lookup[dataset_language])

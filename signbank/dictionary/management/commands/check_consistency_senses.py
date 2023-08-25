"""Create other media files."""

import os
import shutil
from django.core.management.base import BaseCommand
from django.core.exceptions import *
from signbank.dictionary.models import *
from signbank.dictionary.consistency_senses import consistent_senses


class Command(BaseCommand):
    help = 'Check for inconsistent senses: sense order appears twice; ' \
           'more than one sense translation object for language, ' \
           'translation object language does not match, ' \
           'translation order index does not match, ' \
           'gloss does not match'

    def handle(self, *args, **kwargs):
        for gloss in Gloss.objects.all():
            if not gloss.lemma :
                continue
            if not gloss.lemma.dataset:
                continue
            if not consistent_senses(gloss, include_translations=True, allow_empty_language=True):
                print('Inconsistent Gloss ID: ', gloss.id)



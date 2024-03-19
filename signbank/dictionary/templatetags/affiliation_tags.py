"""
Affiliation tags for tagging.
"""

from django.template.library import Library
from signbank.dictionary.models import Gloss, Affiliation, AffiliatedGloss, AffiliatedUser

register = Library()


@register.filter
def get_affiliation_for_gloss(gloss):
    """
    Retrieves a list of ``Affiliation`` objects associated with a gloss and
    stores them in a context variable.
    """

    affiliations_for_gloss = gloss.affiliation_corpus_contains.all()
    return affiliations_for_gloss


def get_affiliations():
    """
    Retrieves a list of ``Affiliation`` objects associated with a gloss and
    stores them in a context variable.
    """

    affiliations = Affiliation.objects.all()
    return affiliations

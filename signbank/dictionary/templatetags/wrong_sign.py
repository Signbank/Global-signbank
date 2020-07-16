from django.template import Library

register = Library()
sWrongSignTag = "video:_wrong_sign"     # This is the Signbank-implementation (Global, ASL) dependent part!

@register.filter
def wrong_sign(qs):
    """Check if instance @qs has a tag indicating that it is a wrong sign.

    The 'wrong-sign-tag' is defined in the database and is Signbank-implementation dependent;
    The particular value used by a signbank must be specified in [sWrongSignTag] above
    """

    # Initialise boolean return
    bHasWrongSign = False
    # Walk the query-set containing all the tag-objects passed on
    for item in qs:
        # Check if the .name part matches the text of the expected wrong sign tag
        if item.name == sWrongSignTag:
            bHasWrongSign = True
    return bHasWrongSign
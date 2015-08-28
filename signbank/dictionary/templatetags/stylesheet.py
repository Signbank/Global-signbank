from django.template import Library

register = Library()

@register.simple_tag
def primary_css():
    """
    Returns the string contained in the setting PRIMARY_CSS - the
    prefix for any media served by the site
    """
    try:
        from django.conf import settings
        return settings.PRIMARY_CSS
    except:
        return ''
 
 
 
@register.simple_tag
def value(value):
    """
    Return value unless it's None in which case we return 'No Value Set'
    """
    if value == None or value == '':
        return '-'
    else:
        return value
 
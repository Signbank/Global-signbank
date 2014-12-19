from signbank.pages.models import Page


def menu(request):
    """Generate a menu hierarchy from the current set of pages
    
    Returns a list of toplevel menu entries
    which are lists of dictionaries each with
    keys 'url', 'title' and 'children', the value of 'children'
    is a similar list of dictionaries.
    """
    
    # find toplevel pages, with no parent and thier children
    (menu, ignore) = find_children(None, request.META['PATH_INFO']) 
    # return a dictionary to be merged with the request context
    return {'menu': menu}
    

def find_children(page, currentURL):
    """Find the child pages of a given page,
    return a list of dictionaries suitable for insertion
    into the menu structure described in menu()"""

    isCurrent = False
    anyCurrent = False
    result = []
    for page in Page.objects.filter(parent=page, publish=True).order_by('index'):
        (children, childCurrent) = find_children(page, currentURL)
        # we're the current page if any of our children are the current page
        # or if we're the current page        
        isCurrent = ((page.url==currentURL) or childCurrent)
        
        # remember if any of the children are the current page
        anyCurrent = (isCurrent or anyCurrent)
        result.append({'url': page.url, 'title': page.title, 'children': children, 'current': isCurrent})

    return (result, anyCurrent)
    
    
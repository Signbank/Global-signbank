from django.db import models
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import Group



class Page(models.Model):
    url = models.CharField(_('URL'), max_length=100, db_index=True)
    title = models.CharField(_('title'), max_length=200)
    content = models.TextField(_('content'), blank=True)
    template_name = models.CharField(_('template name'), max_length=70, blank=True,
        help_text=_("Example: 'pages/contact_page.html'. If this isn't provided, the system will use 'pages/default.html'."))
    publish = models.BooleanField(_('publish'), help_text=_("If this is checked, the page will be included in the site menus."))
    parent = models.ForeignKey('self', blank=True, null=True, help_text=_("Leave blank for a top level menu entry.  Top level entries that have sub-pages should be empty as they will not be linked in the menu."))
    index = models.IntegerField(_('ordering index'), default=0, help_text=_('Used to order pages in the menu'))
    group_required = models.ManyToManyField(Group, null=True, blank=True, help_text=_("This page will only be visible to members of these groups, leave blank to allow anyone to access."))

    class Meta:
        verbose_name = _('page')
        verbose_name_plural = _('pages')
        ordering = ('url', 'index')

    def __unicode__(self):
        return u"%s -- %s" % (self.url, self.title)

    def get_absolute_url(self):
        return self.url

class PageVideo(models.Model):
    page = models.ForeignKey('Page')
    title = models.CharField(_('title'), max_length=200)
    number = models.PositiveIntegerField(_('number'))
    video = models.FileField(upload_to=settings.PAGES_VIDEO_LOCATION, blank=True)

    def __unicode__(self):
        return "Page Video: %s" % (self.title,)


def copy_flatpages():
    """Copy existing flatpages into Pages"""

    from django.contrib.flatpages.models import FlatPage

    for fp in FlatPage.objects.all():
        p = Page(url=fp.url, title=fp.title, content=fp.content, publish=False, index=0)
        p.save()
from django.conf.urls import *
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
import signbank.registration.forms
from django.conf.urls.static import static
from django.views.generic import TemplateView

#These are needed for the urls below
import signbank.pages.views
import signbank.dictionary.urls
import signbank.feedback.urls
import signbank.feedback.views
import signbank.attachments.urls
import signbank.video.urls
import signbank.video.views
import signbank.registration.urls
import django.contrib.auth.views
import django.contrib.admindocs.urls
import django_summernote.urls

from signbank.dictionary.models import Gloss
from signbank.dictionary.adminviews import GlossListView, GlossDetailView, MorphemeListView, DatasetListView
from signbank.dictionary.views import add_image, delete_image, add_new_morpheme, add_handshape_image

from django.contrib import admin
admin.autodiscover()

from signbank.adminsite import publisher_admin

if settings.SHOW_NUMBERSIGNS:
    numbersigns_view = TemplateView.as_view(template_name='numbersigns/numbersigns.html')
else:
    numbersigns_view = TemplateView.as_view(template_name='numbersigns/underconstruction.html')


urlpatterns = [
    url(r'^$', signbank.pages.views.page, name='root_page'),

    url(r'^dictionary/', include(signbank.dictionary.urls, namespace='dictionary')),
    url(r'^feedback/', include(signbank.feedback.urls)),
    url(r'^attachments/', include(signbank.attachments.urls)),
    url(r'^video/', include(signbank.video.urls)),

    url(r'^image/upload/', add_image),
    url(r'^handshapeimage/upload/', add_handshape_image),
    url(r'^image/delete/(?P<pk>[0-9]+)$', delete_image),

    #(r'^register.html', 'signbank.views.index'),
    url(r'^logout.html', django.contrib.auth.views.logout,
                       {'next_page': settings.URL}, "logout"),

    url(r'^spell/twohanded.html$', TemplateView.as_view(template_name='fingerspell/fingerspellingtwohanded.html')),
    url(r'^spell/practice.html$', TemplateView.as_view(template_name='fingerspell/fingerspellingpractice.html')),
    url(r'^spell/onehanded.html$', TemplateView.as_view(template_name='fingerspell/fingerspellingonehanded.html')),
    url(r'^numbersigns.html$', numbersigns_view),

    #Hardcoding a number of special urls:
    url(r'^signs/dictionary/$', signbank.dictionary.views.search),
    url(r'^signs/search/$', GlossListView.as_view()),
    url(r'^signs/show_all/$', GlossListView.as_view(),{'show_all':True}),
    url(r'^signs/add/$', signbank.dictionary.views.add_new_sign),
    url(r'^signs/import_csv/$', signbank.dictionary.views.import_csv),
    url(r'^signs/homonyms/$', signbank.dictionary.views.find_homonyms),
    url(r'^signs/recently_added/$', signbank.dictionary.views.recently_added_glosses),
    url(r'^signs/proposed_new/$', signbank.dictionary.views.proposed_new_signs),
    url(r'^morphemes/dictionary/$', signbank.dictionary.views.search_morpheme),
    url(r'^morphemes/search/$', permission_required('dictionary.search_gloss')(MorphemeListView.as_view())),
    url(r'^morphemes/add/$', permission_required('dictionary.search_gloss')(add_new_morpheme)),
    url(r'^feedback/overview/$', signbank.feedback.views.showfeedback),

    # A standard view for setting the language
    url(r'^i18n/', include('django.conf.urls.i18n')),

    # compatibility with old links - intercept and return 401
    url(r'^index.cfm', TemplateView.as_view(template_name='compat.html')),

   # (r'^accounts/login/', 'django.contrib.auth.views.login'),

    url(r'^accounts/', include(signbank.registration.urls,namespace="registration")),
    url(r'^admin/doc/', include(django.contrib.admindocs.urls)),
    url(r'^admin/', include(admin.site.urls)),

    # special admin sub site
    url(r'^publisher/', include(publisher_admin.urls)),


    url(r'^summernote/', include(django_summernote.urls)),

    url(r'^test/(?P<videofile>.*)$', TemplateView.as_view(template_name="test.html")),

    url(r'reload_signbank/$',signbank.tools.reload_signbank),

    url(r'^datasets/available', DatasetListView.as_view(), name='admin_dataset_view'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


from django.conf.urls import *
from django.contrib.auth.decorators import permission_required
from django.urls import re_path, path, include

import signbank.animation.views

urlpatterns = [
    re_path(r'^animation/(?P<animationid>\d+)$', signbank.animation.views.animation),
    re_path(r'^upload/', signbank.animation.views.addanimation)
    ]

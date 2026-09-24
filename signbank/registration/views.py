"""
Views which allow users to create and activate accounts.
"""
import json
from datetime import date, timedelta

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.translation import gettext_lazy as _
from django.middleware.csrf import get_token
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import REDIRECT_FIELD_NAME, login
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import Site
from django.contrib.sites.requests import RequestSite

from guardian.shortcuts import assign_perm, get_user_perms

from signbank.registration.models import RegistrationProfile
from signbank.registration.forms import RegistrationForm, EmailAuthenticationForm
from signbank.communication.models import generate_communication
from signbank.dictionary.models import Dataset, UserProfile, SearchHistory, Affiliation, AffiliatedUser, SignbankAPIToken
from signbank.dictionary.context_data import get_selected_datasets
from signbank.tools import get_users_without_dataset
from signbank.api_token import create_api_token

API_MANUAL_URL = 'https://signbank.github.io/Global-signbank/'


def activate(request, activation_key, template_name='registration/activate.html'):
    """
    Activates a ``User``'s account, if their key is valid and hasn't
    expired.
    
    By default, uses the template ``registration/activate.html``; to
    change this, pass the name of a template as the keyword argument
    ``template_name``.
    
    Context:
    
        account
            The ``User`` object corresponding to the account, if the
            activation was successful. ``False`` if the activation was
            not successful.
    
        expiration_days
            The number of days for which activation keys stay valid
            after registration.
    
    Template:
    
        registration/activate.html or ``template_name`` keyword
        argument.
    
    """
    activation_key = activation_key.lower() # Normalize before trying anything with it.
    account = RegistrationProfile.objects.activate_user(activation_key)
    account.is_active = True
    account.save()
    return render(request, template_name,
                              { 'account': account,
                                'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS })

def register(request, success_url=settings.PREFIX_URL + '/accounts/register/complete/',
             form_class=RegistrationForm,
             template_name='registration/registration_form.html'):
    """
    Allows a new user to register an account.
    
    Following successful registration, redirects to either
    ``/accounts/register/complete/`` or, if supplied, the URL
    specified in the keyword argument ``success_url``.
    
    By default, ``registration.forms.RegistrationForm`` will be used
    as the registration form; to change this, pass a different form
    class as the ``form_class`` keyword argument. The form class you
    specify must have a method ``save`` which will create and return
    the new ``User``, and that method must accept the keyword argument
    ``profile_callback`` (see below).
    
    To enable creation of a site-specific user profile object for the
    new user, pass a function which will create the profile object as
    the keyword argument ``profile_callback``. See
    ``RegistrationManager.create_inactive_user`` in the file
    ``models.py`` for details on how to write this function.
    
    By default, uses the template
    ``registration/registration_form.html``; to change this, pass the
    name of a template as the keyword argument ``template_name``.
    
    Context:
    
        form
            The registration form.
    
    Template:
    
        registration/registration_form.html or ``template_name``
        keyword argument.
    
    """
    if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
        show_dataset_interface = settings.SHOW_DATASET_INTERFACE_OPTIONS
    else:
        show_dataset_interface = False

    if request.method == 'POST':
        form = form_class(data=request.POST)
        if form.is_valid():
            new_user = form.save()
            request.session['username'] = new_user.username
            request.session['first_name'] = new_user.first_name
            request.session['last_name'] = new_user.last_name
            request.session['email'] = new_user.email
            groups_of_user = [ g.name.replace('_',' ') for g in new_user.groups.all() ]
            request.session['groups'] = groups_of_user

            if hasattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS') and settings.SHOW_DATASET_INTERFACE_OPTIONS:
                list_of_datasets = request.POST.getlist('dataset[]')
                if '' in list_of_datasets:
                    list_of_datasets.remove('')

                group_manager = Group.objects.get(name='Dataset_Manager')

                motivation = request.POST.get('motivation_for_use', '')  # motivation is a required field in the form

                # send email to each of the dataset owners
                current_site = Site.objects.get_current()

                for dataset_name in list_of_datasets:
                    # the datasets are selected via a pulldown list, they should exist
                    dataset_obj = Dataset.objects.get(name=dataset_name)

                    # Notify the dataset owners about (accepted) request for access
                    owners_of_dataset = dataset_obj.owners.all()

                    if dataset_obj.is_public:

                        # Give user access to view the database
                        assign_perm('view_dataset', new_user, dataset_obj)

                        for owner in owners_of_dataset:

                            groups_of_user = owner.groups.all()
                            if not group_manager in groups_of_user:
                                # this owner can't manage users
                                continue

                            mail_template_context = {'dataset': dataset_name,
                                                     'user': new_user,
                                                     'motivation': motivation,
                                                     'site': current_site}

                            subject, message = generate_communication('dataset_to_owner_new_user_given_access',
                                                                      mail_template_context)

                            # for debug purposes on local machine
                            if settings.DEBUG_EMAILS_ON:
                                print('owner of dataset: ', owner.username, ' with email: ', owner.email)
                                print('message: ', message)
                                print('setting: ', settings.DEFAULT_FROM_EMAIL)

                            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [owner.email])

                    else:

                        for owner in owners_of_dataset:

                            groups_of_user = owner.groups.all()
                            if not group_manager in groups_of_user:
                                # this owner can't manage users
                                continue

                            current_site = Site.objects.get_current()

                            mail_template_context = {'dataset': dataset_name,
                                                     'user': new_user,
                                                     'motivation': motivation,
                                                     'site': current_site}

                            subject, message = generate_communication('dataset_to_owner_user_requested_access',
                                                                      mail_template_context)

                            # for debug purposes on local machine
                            if settings.DEBUG_EMAILS_ON:
                                print('owner of dataset: ', owner.username, ' with email: ', owner.email)
                                print('message: ', message)
                                print('setting: ', settings.DEFAULT_FROM_EMAIL)

                            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [owner.email])


                request.session['requested_datasets'] = list_of_datasets
            return HttpResponseRedirect(success_url)
        else:
            # error messages
            messages.add_message(request, messages.ERROR, _('Error processing your request.'))
            # for ff in form.visible_fields():
            #     if ff.errors:
            #         print('form error in field ', ff.name, ': ', ff.errors)
            #         messages.add_message(request, messages.ERROR, ff.errors)

            # create a new empty form, this deletes the erroneous fields
            # form = form_class()
    else:
        # this insures that a preselected dataset is available if we got here from Dataset Details
        form = form_class(request=request)
    return render(request,template_name, {'form': form,
                                          'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface})

# a copy of the login view since we need to change the form to allow longer
# userids (> 30 chars) since we're using email addresses

def mylogin(request, template_name='registration/login.html', redirect_field_name='/signs/recently_added/'):
    """Displays the login form and handles the login action."""

    redirect_to = request.GET[REDIRECT_FIELD_NAME] if REDIRECT_FIELD_NAME in request.GET else ''
    error_message = ''

    if request.method == "POST":
        if REDIRECT_FIELD_NAME in request.POST:
            redirect_to = request.POST[REDIRECT_FIELD_NAME]

        form = EmailAuthenticationForm(data=request.POST)
        if form.is_valid():

            # Count the number of logins
            profile = form.get_user().user_profile_user
            profile.number_of_logins += 1
            profile.save()

            # Expiry date cannot be in the past
            if profile.expiry_date is not None and date.today() > profile.expiry_date:
                form = EmailAuthenticationForm(request)
                error_message = _('This account has expired. Please contact w.stoop@let.ru.nl.')

            else:
                # Light security check -- make sure redirect_to isn't garbage.
                if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
                    redirect_to = settings.LOGIN_REDIRECT_URL
                login(request, form.get_user())
                if request.session.test_cookie_worked():
                    request.session.delete_test_cookie()

                # For logging in API clients
                if "api" in request.GET and request.GET['api'] == 'yes':
                    return HttpResponse(json.dumps({'success': 'true'}), content_type='application/json')

                return HttpResponseRedirect(redirect_to)
        else:
            if "api" in request.GET and request.GET['api'] == 'yes':
                    return HttpResponse(json.dumps({'success': 'false'}), content_type='application/json')
            error_message = _('The username or password is incorrect.')

    else:
        form = EmailAuthenticationForm(request)

    request.session.set_test_cookie()
    try:
        if Site._meta.installed:
            current_site = Site.objects.get_current()
    except AttributeError:
        current_site = RequestSite(request)

    # For logging in API clients
    if request.method == "GET" and "api" in request.GET and request.GET['api'] == 'yes':
        token = get_token(request)
        return HttpResponse(json.dumps({'csrfmiddlewaretoken': token}), content_type='application/json')

    return render(request,template_name, {
        'form': form,
        REDIRECT_FIELD_NAME: settings.URL+redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'allow_registration': settings.ALLOW_REGISTRATION,
        'error_message': error_message})
mylogin = never_cache(mylogin)


def users_without_dataset(request):
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)

    main_dataset = Dataset.objects.get(pk=settings.DEFAULT_DATASET_PK)

    if len(request.POST) > 0:
        users_with_access = []
        for user in request.POST.keys():

            if not 'user' in user:
                continue

            user = User.objects.get(pk=int(user.split('_')[-1]))
            assign_perm('view_dataset', user, main_dataset)

            users_with_access.append(user.first_name + ' ' + user.last_name)

        alert_success = ', '.join(users_with_access)
    else:
        alert_success = None

    return render(request, 'users_without_dataset.html', {'users_without_dataset': get_users_without_dataset(),
                                                          'main_dataset_name': main_dataset.name,
                                                          'alert_success': alert_success})


def user_profile(request):

    user_object = User.objects.get(username=request.user)
    user_profile = UserProfile.objects.get(user=user_object)
    expiry = getattr(user_profile, 'expiry_date')
    today = date.today()
    if expiry:
        delta = expiry - today
    else:
        delta = None
    selected_datasets = get_selected_datasets(request)
    view_permit_datasets = []
    for dataset in Dataset.objects.all():
        permissions_for_dataset = get_user_perms(request.user, dataset)
        if 'view_dataset' in permissions_for_dataset:
            view_permit_datasets.append(dataset)
    change_permit_datasets = []
    for dataset_user_can_view in view_permit_datasets:
        if 'change_dataset' in get_user_perms(request.user, dataset_user_can_view):
            change_permit_datasets.append(dataset_user_can_view)
    user_has_queries = SearchHistory.objects.filter(user=request.user).count()
    user_can_change_glosses = len(change_permit_datasets) > 0
    possible_affiliations = [aff for aff in Affiliation.objects.all()]
    user_affiliation = [au for au in AffiliatedUser.objects.filter(user=request.user)]
    user_api_tokens = list(user_object.tokens.all())
    return render(request, 'user_profile.html', {'selected_datasets': selected_datasets,
                                                 'view_permit_datasets': view_permit_datasets,
                                                 'change_permit_datasets': change_permit_datasets,
                                                 'user_can_change_glosses': user_can_change_glosses,
                                                 'user_has_queries': user_has_queries,
                                                 'possible_affiliations': possible_affiliations,
                                                 'user_affiliation': user_affiliation,
                                                 'user_api_tokens': user_api_tokens,
                                                 'api_token_expiry_choices': API_TOKEN_EXPIRY_CHOICES,
                                                 'api_token_default_expiry_days': API_TOKEN_DEFAULT_EXPIRY_DAYS,
                                                 'api_token_default_rate_limit': getattr(settings, 'API_TOKEN_DEFAULT_RATE_LIMIT', None),
                                                 'api_manual_url': API_MANUAL_URL,
                                                 'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
                                                 'expiry': expiry,
                                                 'delta': delta})


API_TOKEN_EXPIRY_CHOICES = [(30, _("30 days")), (90, _("90 days")), (180, _("180 days")),
                            (365, _("1 year")), (0, _("Never"))]
API_TOKEN_DEFAULT_EXPIRY_DAYS = 90


@login_required
@require_POST
def auth_token(request):
    """Generate a new API token for the user; the token itself is returned once and never stored"""
    name = request.POST.get('name', '').strip()[:100]

    try:
        expiry_days = int(request.POST.get('expiry_days', API_TOKEN_DEFAULT_EXPIRY_DAYS))
    except ValueError:
        expiry_days = -1
    if expiry_days not in [days for days, label in API_TOKEN_EXPIRY_CHOICES]:
        return JsonResponse({'errors': [str(_("Invalid expiry period."))]}, status=400)
    expires_at = timezone.now() + timedelta(days=expiry_days) if expiry_days else None

    rate_limit = request.POST.get('rate_limit', '').strip()
    if rate_limit:
        if not rate_limit.isdigit() or int(rate_limit) < 1:
            return JsonResponse({'errors': [str(_("The rate limit must be a positive number."))]}, status=400)
        rate_limit = int(rate_limit)
        default_rate_limit = getattr(settings, 'API_TOKEN_DEFAULT_RATE_LIMIT', None)
        if default_rate_limit and rate_limit > default_rate_limit:
            return JsonResponse({'errors': [str(_("The rate limit can be at most %(limit)s requests per hour.")
                                                % {'limit': default_rate_limit})]}, status=400)
    else:
        rate_limit = None

    read_only = request.POST.get('read_only') in ['on', 'true', '1']

    signbank_token, new_token = create_api_token(request.user, name=name, expires_at=expires_at,
                                                 rate_limit=rate_limit, read_only=read_only)
    return JsonResponse({'new_token': new_token, 'token_id': signbank_token.id})


@login_required
@require_POST
def delete_auth_token(request, token_id):
    """Delete (revoke) one of the user's own API tokens"""
    deleted, _deleted_per_model = SignbankAPIToken.objects.filter(pk=token_id, signbank_user=request.user).delete()
    if deleted:
        messages.add_message(request, messages.INFO, _("The API token has been deleted."))
    else:
        messages.add_message(request, messages.ERROR, _("The API token could not be found."))
    return HttpResponseRedirect(reverse('registration:user_profile'))

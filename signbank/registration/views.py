"""
Views which allow users to create and activate accounts.
"""
from datetime import date

from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.middleware.csrf import get_token
from django.contrib.auth.models import Group, User
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.contrib.auth import REDIRECT_FIELD_NAME, login, views as auth_views
from django.views.decorators.cache import never_cache
from django.contrib.sites.models import Site
from django.contrib.sites.requests import RequestSite

from guardian.shortcuts import assign_perm, get_user_perms

from signbank.registration.models import RegistrationProfile
from signbank.registration.forms import RegistrationForm, SignbankAuthenticationForm
from signbank.dictionary.models import Dataset, UserProfile, SearchHistory, AffiliatedUser, SignbankAPIToken
from signbank.dictionary.context_data import get_selected_datasets
from signbank.tools import get_users_without_dataset
from signbank.api_token import generate_auth_token, hash_token


def activate(request, activation_key, template_name='registration/activate.html'):
    """Activates a ``User``'s account, if their key is valid and hasn't expired."""
    activation_key = activation_key.lower()
    account = RegistrationProfile.objects.activate_user(activation_key)
    account.is_active = True
    account.save()
    return render(request, template_name, {'account': account, 'expiration_days': settings.ACCOUNT_ACTIVATION_DAYS})


def register(request, success_url=settings.PREFIX_URL + '/accounts/register/complete/',
             form_class=RegistrationForm,
             template_name='registration/registration_form.html'):
    """Allows a new user to register an account."""
    show_dataset_interface = getattr(settings, 'SHOW_DATASET_INTERFACE_OPTIONS', False)

    if request.method != 'POST':
        context = {'form': form_class(), 'SHOW_DATASET_INTERFACE_OPTIONS': show_dataset_interface}
        return render(request, template_name, context)

    form = form_class(data=request.POST)
    if not form.is_valid():
        messages.add_message(request, messages.ERROR, _("Error processing your request."))
        context = {"form": form, "SHOW_DATASET_INTERFACE_OPTIONS": show_dataset_interface}
        return render(request, template_name, context)

    new_user = form.save()
    add_user_data_to_session(new_user, request)

    if not show_dataset_interface:
        return HttpResponseRedirect(success_url)

    send_mail_to_dataset_owners(new_user, request)

    return HttpResponseRedirect(success_url)


def send_mail_to_dataset_owners(new_user: User, request):
    """Sends emails to dataset owners [helper for 'register' view]"""
    group_manager = Group.objects.get(name='Dataset_Manager')
    motivation = request.POST.get('motivation_for_use', '')
    current_site = Site.objects.get_current()

    list_of_datasets = [dataset for dataset in request.POST.getlist("dataset[]") if dataset != ""]
    request.session["requested_datasets"] = list_of_datasets
    for dataset_name in list_of_datasets:
        dataset_obj = Dataset.objects.get(name=dataset_name)
        if dataset_obj.is_public:
            assign_perm("view_dataset", new_user, dataset_obj)
            template_name_subject = 'registration/dataset_to_owner_new_user_given_access_subject.txt'
            template_name_message = 'registration/dataset_to_owner_new_user_given_access.txt'
        else:
            template_name_subject = 'registration/dataset_to_owner_user_requested_access_subject.txt'
            template_name_message = 'registration/dataset_to_owner_user_requested_access.txt'

        for owner in dataset_obj.owners.all():
            if group_manager not in owner.groups.all():
                continue

            subject = render_to_string(template_name_subject, context={'dataset': dataset_name, 'site': current_site})
            subject = ''.join(subject.splitlines())
            message_context = {
                'dataset': dataset_name,
                'new_user_username': new_user.username,
                'new_user_firstname': new_user.first_name,
                'new_user_lastname': new_user.last_name,
                'new_user_email': new_user.email,
                'motivation': motivation,
                'site': current_site
            }
            message = render_to_string(template_name_message, context=message_context)
            send_mail_with_debug(message, owner, subject)


def send_mail_with_debug(message, owner, subject):
    """Send an email or, if DEBUG_EMAILS_ON, print info"""
    if not settings.DEBUG_EMAILS_ON:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [owner.email])
    else:
        print('owner of dataset: ', owner.username, ' with email: ', owner.email)
        print('message: ', message)
        print('setting: ', settings.DEFAULT_FROM_EMAIL)


def add_user_data_to_session(new_user: User, request):
    """Populates the request.session with data from new_user [helper for 'register' view]"""
    request.session['username'] = new_user.username
    request.session['first_name'] = new_user.first_name
    request.session['last_name'] = new_user.last_name
    request.session['email'] = new_user.email
    groups_of_user = [g.name.replace('_', ' ') for g in new_user.groups.all()]
    request.session['groups'] = groups_of_user


def signbank_login(request, template_name='registration/login.html'):
    """Displays the login form and handles the login action."""

    # For logging in API clients
    if request.method == "GET" and request.GET.get('api') == 'yes':
        token = get_token(request)
        request.session.set_test_cookie()
        return JsonResponse({'csrfmiddlewaretoken': token})

    redirect_to = request.GET.get(REDIRECT_FIELD_NAME, '')
    current_site = get_current_site(request)

    context = {
        REDIRECT_FIELD_NAME: settings.URL+redirect_to,
        'site': current_site,
        'site_name': current_site.name,
        'allow_registration': settings.ALLOW_REGISTRATION,
        'error_message': ''
    }

    if request.method != 'POST':
        context['form'] = SignbankAuthenticationForm(request)
        return render(request, template_name, context)

    if REDIRECT_FIELD_NAME in request.POST:
        context[REDIRECT_FIELD_NAME] = redirect_to = settings.URL+request.POST[REDIRECT_FIELD_NAME]

    form = SignbankAuthenticationForm(data=request.POST)
    if not form.is_valid():
        if request.GET.get('api') == 'yes':
            return JsonResponse({'success': 'false'})
        context['error_message'] = _('The username or password is incorrect.')
        request.session.set_test_cookie()
        return render(request, template_name, context)

    profile = form.get_user().user_profile_user
    profile.number_of_logins += 1
    profile.save()

    if profile.expiry_date is not None and date.today() > profile.expiry_date:
        context['form'] = SignbankAuthenticationForm(request)
        context['error_message'] = _('This account has expired. Please contact w.stoop@let.ru.nl.')
        request.session.set_test_cookie()
        return render(request, template_name, context)

    login(request, form.get_user())

    if request.session.test_cookie_worked():
        request.session.delete_test_cookie()

    if request.GET.get('api') == 'yes':
        return JsonResponse({'success': 'true'})

    if not redirect_to or '//' in redirect_to or ' ' in redirect_to:
        redirect_to = settings.LOGIN_REDIRECT_URL
    return HttpResponseRedirect(redirect_to)


signbank_login = never_cache(signbank_login)


def get_current_site(request) -> Site:
    try:
        if Site._meta.installed:
            return Site.objects.get_current()
    except AttributeError:
        return RequestSite(request)
    return None


def users_without_dataset(request):
    """Show users that are not linked to any dataset"""
    if not request.user.is_superuser:
        return HttpResponse('Unauthorized', status=401)

    main_dataset = Dataset.objects.get(pk=settings.DEFAULT_DATASET_PK)

    context = {
        'users_without_dataset': get_users_without_dataset(),
        'main_dataset_name': main_dataset.name,
        'alert_success': None
    }

    if not request.POST:
        return render(request, "users_without_dataset.html", context)

    users_with_access = []
    user_keys = (user for user in request.POST.keys() if 'user' in user)
    for user in user_keys:
        user = User.objects.get(pk=int(user.split('_')[-1]))
        assign_perm('view_dataset', user, main_dataset)
        users_with_access.append(user.first_name + ' ' + user.last_name)

    context['alert_success'] = ', '.join(users_with_access)
    return render(request, 'users_without_dataset.html', context)


def user_profile(request):
    """Show profile info to user"""
    user = request.user
    profile = UserProfile.objects.get(user=user)
    expiry = profile.expiry_date
    delta = expiry - date.today() if expiry else None

    selected_datasets = get_selected_datasets(request)
    view_permit_datasets = [
        dataset for dataset in Dataset.objects.all()
        if 'view_dataset' in get_user_perms(user, dataset)
    ]
    change_permit_datasets = [
        dataset for dataset in view_permit_datasets
        if 'change_dataset' in get_user_perms(user, dataset)
    ]

    user_has_queries = SearchHistory.objects.filter(user=user).exists()
    user_affiliation = AffiliatedUser.objects.filter(user=user)
    user_api_tokens = user.tokens.all()
    context = {
        'selected_datasets': selected_datasets,
        'view_permit_datasets': view_permit_datasets,
        'change_permit_datasets': change_permit_datasets,
        'user_has_queries': user_has_queries,
        'user_affiliation': user_affiliation,
        'user_api_tokens': user_api_tokens,
        'SHOW_DATASET_INTERFACE_OPTIONS': settings.SHOW_DATASET_INTERFACE_OPTIONS,
        'expiry': expiry,
        'delta': delta
    }
    return render(request, 'user_profile.html', context)


def auth_token(request):
    """Returns new authentication token"""
    user = request.user
    new_token = generate_auth_token()
    hashed_token = hash_token(new_token)
    SignbankAPIToken.objects.create(signbank_user=user, api_token=hashed_token)
    return JsonResponse({'new_token': new_token})


class SignbankPasswordResetView(auth_views.PasswordResetView):
    success_url = reverse_lazy('registration:password_reset_done')


class SignbankPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    success_url = reverse_lazy('registration:password_reset_complete')


import os
from signbank.feedback.models import *
from django import forms
from django.shortcuts import render, get_object_or_404, redirect, render_to_response
from django.template import Context, RequestContext, loader
from django.conf import settings 
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib import messages
from django.utils.safestring import mark_safe

import time

def index(request):
    return render(request,'feedback/index.html',
                              { 
                               'language': settings.LANGUAGE_NAME,
                               'country': settings.COUNTRY_NAME,
                               'title':"Leave Feedback"})



@login_required
def interpreterfeedback(request, glossid=None):
      
    if request.method == "POST":
        
        if 'action' in request.POST and 'delete_all' in request.POST['action']:
            gloss = get_object_or_404(Gloss, pk=glossid)
            fbset = gloss.interpreterfeedback_set.all()
            fbset.delete()        
        elif 'action' in request.POST and 'delete' in request.POST['action']:
            fbid = request.POST['id']
            fb = get_object_or_404(InterpreterFeedback, pk=fbid)
            
            fb.delete()
        else:
            gloss = get_object_or_404(Gloss, pk=glossid)
        
            form = InterpreterFeedbackForm(request.POST, request.FILES)
            if form.is_valid():        
            
            
                fb = form.save(commit=False)
                fb.user = request.user
                fb.gloss = gloss
                fb.save()
    
        # redirect to the gloss page 
        return HttpResponseRedirect(reverse('dictionary:admin_gloss_view', kwargs={'pk': glossid}))
    else:
        
        # generate a page listing the feedback from interpreters
        
        notes = InterpreterFeedback.objects.all()
    
        general = GeneralFeedback.objects.filter(status='unread', user__groups__name='Interpreter')
        missing = MissingSignFeedback.objects.filter(status='unread', user__groups__name='Interpreter')
        signfb = SignFeedback.objects.filter(status='unread', user__groups__name='Interpreter')
        
        return render(request,'feedback/interpreter.html',
                                   {'notes': notes,
                                    'general': general,
                                    'missing': missing,
                                    'signfb': signfb})


        


@login_required
def generalfeedback(request):
    feedback = GeneralFeedback()
    valid = False
   
    if request.method == "POST":
        form = GeneralFeedbackForm(request.POST, request.FILES)
        if form.is_valid():           
            
            feedback = GeneralFeedback(user=request.user)
            if 'comment' in form.cleaned_data: 
                feedback.comment = form.cleaned_data['comment'] 
            
            if 'video' in form.cleaned_data and form.cleaned_data['video'] != None:
                feedback.video = form.cleaned_data['video']
                
            feedback.save()
            valid = True
            request_path = request.path
            if 'return' in request.GET:
                sourcepage = request.GET['return']
            else:
                sourcepage = ""

            messages.add_message(request, messages.INFO, mark_safe(
                    'Thank you. Your feedback has been saved. <a href="' + sourcepage + '">Return to Previous Page</a>'))

            # return HttpResponseRedirect("")
            return render(request, 'feedback/generalfeedback.html', {'language': settings.LANGUAGE_NAME,
                                                                    'country': settings.COUNTRY_NAME,
                                                                    'title':"General Feedback",
                                                                    'form': form,
                                                                    'valid': valid })
    else:
        form = GeneralFeedbackForm()

    return render(request,"feedback/generalfeedback.html",
                              {
                               'language': settings.LANGUAGE_NAME,
                               'country': settings.COUNTRY_NAME,
                               'title':"General Feedback",
                               'form': form,
                               'valid': valid })

@login_required
def missingsign(request):

    posted = False # was the feedback posted?
    
    if request.method == "POST":
        
        fb = MissingSignFeedback()
        fb.user = request.user
        
        form = MissingSignFeedbackForm(request.POST, request.FILES)
        
        if form.is_valid(): 
            
            # either we get video of the new sign or we get the 
            # description via the form
            
            if 'video' in form.cleaned_data and form.cleaned_data['video'] != None:
                fb.video = form.cleaned_data['video']

            # else:
            #     # get sign details from the form
            #     fb.handform = form.cleaned_data['handform']
            #     fb.handshape = form.cleaned_data['handshape']
            #     fb.althandshape = form.cleaned_data['althandshape']
            #     fb.location = form.cleaned_data['location']
            #     fb.relativelocation = form.cleaned_data['relativelocation']
            #     fb.handbodycontact = form.cleaned_data['handbodycontact']
            #     fb.handinteraction = form.cleaned_data['handinteraction']
            #     fb.direction = form.cleaned_data['direction']
            #     fb.movementtype = form.cleaned_data['movementtype']
            #     fb.smallmovement = form.cleaned_data['smallmovement']
            #     fb.repetition = form.cleaned_data['repetition']
            
            # these last two are required either way (video or not)
            fb.meaning = form.cleaned_data['meaning']
            fb.comments = form.cleaned_data['comments']
    
            fb.save()
            posted = True

    else:
        form = MissingSignFeedbackForm()        
  
    
    return render(request,'feedback/missingsign.html',
                               {
                               'language': settings.LANGUAGE_NAME,
                               'country': settings.COUNTRY_NAME,
                                'title':"Report a Missing Sign",
                                'posted': posted,
                                'form': form})


@permission_required('feedback.delete_generalfeedback')
def showfeedback(request):
    """View to list the feedback that's been left on the site"""
    
    general = GeneralFeedback.objects.filter(status='unread')
    missing = MissingSignFeedback.objects.filter(status='unread')
    signfb = SignFeedback.objects.filter(status__in=('unread', 'read'))
    
    return render(request,"feedback/show.html",
                              {'general': general,    
                              'missing': missing,
                              'signfb': signfb})

    

@login_required
def glossfeedback(request, glossid):

    request_path = request.path

    allkwds = []
    if 'morpheme' in request_path:
        morpheme = get_object_or_404(Morpheme, id=glossid)
        allkwds = morpheme.translation_set.all()
    else:
        gloss = get_object_or_404(Gloss, id=glossid)
        allkwds = gloss.translation_set.all()
    if len(allkwds) == 0:
        trans = Translation()
    else:
        trans = allkwds[0]
    
    return recordsignfeedback(request, trans, 1, len(allkwds))


# Feedback on individual signs
@login_required
def signfeedback(request, keyword, n):
    """View or give feedback on a sign"""
    
    n = int(n)
    word = get_object_or_404(Keyword, text=keyword)
    
    # returns (matching translation, number of matches) 
    (trans, total) =  word.match_request(request, n)
    
    return recordsignfeedback(request, trans, n, total)
    
    
def recordsignfeedback(request, trans, n, total):
    """Do the work of recording feedback for a sign or gloss"""
    
    # get the page to return to from the get request
    if 'return' in request.GET:
        sourcepage = request.GET['return']
    else:
        sourcepage = ""

    # return to the comment page to show message
    request_path = request.path

    valid = False
    
    if request.method == "POST":
        feedback_form = SignFeedbackForm(request.POST)
        
        if feedback_form.is_valid():
            # get the clean (normalised) data from the feedback_form
            clean = feedback_form.cleaned_data
            morpheme_toggle = 1 if 'morpheme' in request_path else 0
            # create a SignFeedback object to store the result in the db
            try:
                sfb = SignFeedback(
                    isAuslan=clean['isAuslan'],
                    whereused=clean['whereused'],
                    like=morpheme_toggle, #['like'],
                    use=clean['use'],
                    suggested=clean['suggested'],
                    correct=clean['correct'],
                    kwnotbelong=clean['kwnotbelong'],
                    comment=clean['comment'],
                    user=request.user,
                    translation_id = request.POST["translation_id"]
                    )
                sfb.save()
                valid = True
                # redirect to the original page
                if 'morpheme' in request_path:
                    messages.add_message(request, messages.INFO, mark_safe('Thank you. Your feedback has been saved. <a href="'+sourcepage+'">Return to Morpheme</a>'))
                else:
                    messages.add_message(request, messages.INFO, mark_safe('Thank you. Your feedback has been saved. <a href="'+sourcepage+'">Return to Sign</a>'))

                # return HttpResponseRedirect("")
                return render(request, 'feedback/signfeedback.html', { 'feedback_form': feedback_form,
                                                                       'sourcepage': sourcepage})
            except:
                messages.add_message(request, messages.ERROR,'There was an error processing your feedback data.')

    feedback_form = SignFeedbackForm()
        
    return render(request,"feedback/signfeedback.html",
                              {'translation': trans,
                               'n': n, 
                               'total': total,   
                               'feedback_form': feedback_form, 
                               'valid': valid,
                               'sourcepage': sourcepage,
                               'language': settings.LANGUAGE_NAME})

#--------------------
#  deleting feedback
#--------------------

import django
# @permission_required('feedback.delete_generalfeedback')
def delete(request, kind, id):
    """Mark a feedback item as deleted, kind 'signfeedback', 'generalfeedback' or 'missingsign'"""

    # print('delete feedback kind: ', kind)
    if kind == 'sign':
        KindModel = django.apps.apps.get_model('feedback', 'SignFeedback')
    elif kind == 'general':
        KindModel = django.apps.apps.get_model('feedback', 'GeneralFeedback')
    elif kind == 'missingsign':
        KindModel = django.apps.apps.get_model('feedback', 'MissingSignFeedback')
    else:
        raise Http404

    field = request.POST.get('id', '')
    value = request.POST.get('value', '')

    print('feedback delete id: ', field)
    (what, fbid) = field.split('_')

    if value == 'confirmed':
        print('confirmed')
    item = get_object_or_404(KindModel, pk=fbid)
    print('feedback id: ', id, ', delete kind: ', kind, ', KindModel: ', KindModel, ', what: ', what)
    # mark as deleted
    item.status = 'deleted'
    item.save()

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)
    



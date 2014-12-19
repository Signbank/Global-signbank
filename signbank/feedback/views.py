
import os
from models import *
from django import forms
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import Context, RequestContext, loader
from django.conf import settings 
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse

import time

def index(request):
    return render_to_response('feedback/index.html',
                              { 
                               'language': settings.LANGUAGE_NAME,
                               'country': settings.COUNTRY_NAME,
                               'title':"Leave Feedback"},
                              context_instance=RequestContext(request))



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
        
        return render_to_response('feedback/interpreter.html',
                                   {'notes': notes,
                                    'general': general,
                                    'missing': missing,
                                    'signfb': signfb,
                                   },
                               context_instance=RequestContext(request))


        


@login_required
def generalfeedback(request):
    feedback = GeneralFeedback()
    valid = False
   
    if request.method == "POST":
        form = GeneralFeedbackForm(request.POST, request.FILES)
        if form.is_valid():           
            
            feedback = GeneralFeedback(user=request.user)
            if form.cleaned_data.has_key('comment'): 
                feedback.comment = form.cleaned_data['comment'] 
            
            if form.cleaned_data.has_key('video') and form.cleaned_data['video'] != None:
                feedback.video = form.cleaned_data['video']
                
            feedback.save()
            valid = True
    else:
        form = GeneralFeedbackForm()

    return render_to_response("feedback/generalfeedback.html",
                              {
                               'language': settings.LANGUAGE_NAME,
                               'country': settings.COUNTRY_NAME,
                               'title':"General Feedback",
                               'form': form,
                               'valid': valid },
                               context_instance=RequestContext(request)
                              )

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
            
            if form.cleaned_data.has_key('video') and form.cleaned_data['video'] != None:
                fb.video = form.cleaned_data['video']

            else:
                # get sign details from the form 
                fb.handform = form.cleaned_data['handform'] 
                fb.handshape = form.cleaned_data['handshape']
                fb.althandshape = form.cleaned_data['althandshape']
                fb.location = form.cleaned_data['location']
                fb.relativelocation = form.cleaned_data['relativelocation']
                fb.handbodycontact = form.cleaned_data['handbodycontact']
                fb.handinteraction = form.cleaned_data['handinteraction']
                fb.direction = form.cleaned_data['direction']
                fb.movementtype = form.cleaned_data['movementtype']
                fb.smallmovement = form.cleaned_data['smallmovement']
                fb.repetition = form.cleaned_data['repetition']
            
            # these last two are required either way (video or not)
            fb.meaning = form.cleaned_data['meaning']
            fb.comments = form.cleaned_data['comments']
    
            fb.save()
            posted = True
    else:
        form = MissingSignFeedbackForm()        
  
    
    return render_to_response('feedback/missingsign.html',
                               {
                               'language': settings.LANGUAGE_NAME,
                               'country': settings.COUNTRY_NAME,
                                'title':"Report a Missing Sign",
                                'posted': posted,
                                'form': form
                                },
                              context_instance=RequestContext(request))

                              
#-----------
# views to show feedback to Trevor et al
#-----------

@permission_required('feedback.delete_generalfeedback')
def showfeedback(request):
    """View to list the feedback that's been left on the site"""
    
    general = GeneralFeedback.objects.filter(status='unread')
    missing = MissingSignFeedback.objects.filter(status='unread')
    signfb = SignFeedback.objects.filter(status__in=('unread', 'read'))
    
    return render_to_response("feedback/show.html",
                              {'general': general,    
                              'missing': missing,
                              'signfb': signfb,
                              }, 
                              context_instance=RequestContext(request))
    
    
    

@login_required
def glossfeedback(request, glossid):
    
    gloss = get_object_or_404(Gloss, idgloss=glossid)
    
    # construct a translation so we can record feedback against it
    # really should have recorded feedback for a gloss, not a sign
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
    if request.GET.has_key('return'):
        sourcepage = request.GET['return']
    else:
        sourcepage = ""
    
    if request.GET.has_key('lastmatch'):
        lastmatch = request.GET['lastmatch']
    else:
        lastmatch = None
    
    valid = False
    
    if request.method == "POST":
        feedback_form = SignFeedbackForm(request.POST)
        
        if feedback_form.is_valid():
            # get the clean (normalised) data from the feedback_form
            clean = feedback_form.cleaned_data
            # create a SignFeedback object to store the result in the db
            sfb = SignFeedback(
                isAuslan=clean['isAuslan'],
                whereused=clean['whereused'],
                like=clean['like'],
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
            if lastmatch:
                return HttpResponseRedirect(sourcepage+"?lastmatch="+lastmatch+"&feedbackmessage=Thank you. Your feedback has been saved.")
            else:
                return HttpResponseRedirect(sourcepage+"?feedbackmessage=Thank you. Your feedback has been saved.")                    
    else:
        feedback_form = SignFeedbackForm()
        
    return render_to_response("feedback/signfeedback.html",
                              {'translation': trans,
                               'n': n, 
                               'total': total,   
                               'feedback_form': feedback_form, 
                               'valid': valid,
                               'sourcepage': sourcepage,
                               'lastmatch': lastmatch,
                               'language': settings.LANGUAGE_NAME,
                               },
                               context_instance=RequestContext(request))


#--------------------
#  deleting feedback
#--------------------
@permission_required('feedback.delete_generalfeedback')
def delete(request, kind, id):
    """Mark a feedback item as deleted, kind 'signfeedback', 'generalfeedback' or 'missingsign'"""
    
    if kind == 'sign':
        kind = SignFeedback
    elif kind == 'general':
        kind = GeneralFeedback
    elif kind == 'missingsign':
        kind = MissingSignFeedback
    else:
        raise Http404
    
    item = get_object_or_404(kind, id=id)
    # mark as deleted
    item.status = 'deleted'
    item.save()

    # return to referer
    if request.META.has_key('HTTP_REFERER'):
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)
    



from django.shortcuts import render, get_object_or_404, redirect
from django.template import Context, RequestContext
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.conf import settings
from signbank.video.models import Video, GlossVideo, GlossVideoHistory
from signbank.video.forms import VideoUploadForm, VideoUploadForGlossForm
# from django.contrib.auth.models import User
# from datetime import datetime as DT
import os
import re
import glob
import shutil

from signbank.dictionary.models import Gloss, DeletedGlossOrMedia
from signbank.settings.base import GLOSS_VIDEO_DIRECTORY, WRITABLE_FOLDER
from signbank.settings.server_specific import FFMPEG_PROGRAM

from signbank.tools import generate_still_image, get_default_annotationidglosstranslation

def addvideo(request):
    """View to present a video upload form and process
    the upload"""

    if request.method == 'POST':

        form = VideoUploadForGlossForm(request.POST, request.FILES)
        if form.is_valid():

            gloss_id = form.cleaned_data['gloss_id']
            gloss = get_object_or_404(Gloss, pk=gloss_id)

            vfile = form.cleaned_data['videofile']
            
            # construct a filename for the video, use sn
            # if present, otherwise use idgloss+gloss id
            if gloss.sn != None:
                vfile.name = str(gloss.sn) + ".mp4"
            else:
                vfile.name = gloss.idgloss + "-" + str(gloss.pk) + ".mp4"

            redirect_url = form.cleaned_data['redirect']

            # deal with any existing video for this sign

            dir_path = os.path.join(WRITABLE_FOLDER.encode('utf-8'), GLOSS_VIDEO_DIRECTORY.encode('utf-8'))
            sub_dir = gloss.idgloss[:2]
            import urllib.parse
            quoted_filename = urllib.parse.quote(gloss.idgloss, safe='')
            filename = quoted_filename + '-' + str(gloss.pk) + '.mp4'
            path = os.path.join(dir_path, sub_dir.encode('utf-8'), filename.encode('utf-8'))

            goal_folder = os.path.join(dir_path, sub_dir.encode('utf-8'))
            exists_goal_folder = os.path.exists(goal_folder)

            goal_filename = gloss.idgloss + '-' + str(gloss.pk) + '.mp4'
            goal_location_str = os.path.join(goal_folder, goal_filename.encode('utf-8'))

            # test for other video files for this gloss.pk with a different filename, such as version or old idgloss
            if exists_goal_folder:

                files = [f for f in os.listdir(goal_folder)]
                try:
                    for filename in files:
                        unicode_filename = filename.decode('utf-8')

                        if re.match('.*\-'+str(gloss.pk)+'(\.|_).*', unicode_filename):
                            file_to_remove = os.path.join(goal_folder,filename)
                            if os.path.exists(file_to_remove):
                                os.remove(file_to_remove)

                except OSError:
                    return None

            else:
                # make a new goal folder
                os.makedirs(goal_folder,mode=0o755)
            # clean up the database entry for an old file, if necessary

            video_links_count = GlossVideo.objects.filter(gloss=gloss).count()
            video_links_objects = GlossVideo.objects.filter(gloss=gloss)

            if video_links_count > 0:
                # delete the old video object links stored in the database
                for video_object in video_links_objects:
                    video_object.delete()
            # make a new GlossVideo object for the new file, quote the name to account for special characters in the database
            import urllib.parse
            quoted_filename = urllib.parse.quote(vfile.name, safe='')
            vfile.name = quoted_filename
            video = GlossVideo(videofile=vfile, gloss=gloss)
            video.save()

            quoted_base_filename = os.path.basename(vfile.name)
            fname, fext = os.path.splitext(quoted_base_filename)
            filename_small = fname + '_small' + fext
            goal_folder_small = os.path.join(WRITABLE_FOLDER, GLOSS_VIDEO_DIRECTORY, sub_dir)
            goal_location_small = os.path.join(goal_folder_small, filename_small)
            goal_location_resize = WRITABLE_FOLDER + GLOSS_VIDEO_DIRECTORY + '/' + sub_dir + '/' + quoted_base_filename
            #Make sure the rights of the new file are okay
            if os.path.exists(path):
                try:
                    os.chmod(path,0o664)
                except:
                    print('system error changing video location rights: ', path)
            else:
                print('error with video destination inside of video/views.py:addvideo')

            log_entry = GlossVideoHistory(action="upload", gloss=gloss, actor=request.user,
                                          uploadfile=vfile, goal_location=goal_location_str)
            log_entry.save()

            # Issue #197: convert to thumbnail
            try:
                from CNGT_scripts.python.resizeVideos import VideoResizer
                # local copy for debugging purposes
                # from signbank.video.resizeVideos import VideoResizer
                resizer = VideoResizer([goal_location_resize], FFMPEG_PROGRAM, 180, 0, 0)
                resizer.run()
            except:
                print("Error resizing video: ", path)

            # Issue #214: generate still image
            try:
                from signbank.tools import generate_still_image
                generate_still_image(sub_dir, goal_folder_small, filename_small)
            except:
                print('Error generating still image')

            if os.path.exists(goal_location_small):
                os.chmod(goal_location_small,0o664)
            else:
                print('error with small video destination inside of video/views.py:addvideo')

            return redirect(redirect_url)

    # if we can't process the form, just redirect back to the
    # referring page, should just be the case of hitting
    # Upload without choosing a file but could be
    # a malicious request, if no referrer, go back to root
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)

@login_required
def deletevideo(request, videoid):
    """Remove the video for this gloss, if there is an older version
    then reinstate that as the current video (act like undo)"""

    if request.method == "POST":
        # deal with any existing video for this sign
        gloss = get_object_or_404(Gloss, pk=videoid)
        vids = GlossVideo.objects.filter(gloss=gloss).order_by('version')
        for v in vids:
            # this will remove the most recent video, ie it's equivalent
            # to delete if version=0
            v.reversion(revert=True)

            # Issue #162: log the deletion history
            log_entry = GlossVideoHistory(action="delete", gloss=gloss,
                                          actor=request.user,
                                          uploadfile=os.path.basename(v.videofile.name),
                                          goal_location=v.videofile.path)
            log_entry.save()

        gloss_video_filename = gloss.get_video_path_prefix()
        gloss_basename = os.path.basename(gloss_video_filename)
        fpath, fname = os.path.split(gloss.get_video_path())

        import urllib.parse
        quoted_filename = urllib.parse.quote(gloss_basename)
        quoted_path = os.path.join(fpath, quoted_filename + '.mp4')

        filename_small = quoted_filename + '_small' + '.mp4'
        gloss_video_path_small = os.path.join(WRITABLE_FOLDER, filename_small)
        gloss_video_path = os.path.join(WRITABLE_FOLDER, quoted_path)
        #Extra check: if the file is still there, delete it manually
        if os.path.exists(gloss_video_path):
            os.remove(gloss_video_path)
        if os.path.exists(gloss_video_path_small):
            os.remove(gloss_video_path_small)

    default_annotationidglosstranslation = get_default_annotationidglosstranslation(gloss)

    deleted_video = DeletedGlossOrMedia()
    deleted_video.item_type = 'video'
    deleted_video.idgloss = gloss.idgloss
    deleted_video.annotation_idgloss = default_annotationidglosstranslation
    deleted_video.old_pk = gloss.pk
    deleted_video.filename = gloss.get_video_path()
    deleted_video.save()

    # return to referer
    if 'HTTP_REFERER' in request.META:
        url = request.META['HTTP_REFERER']
    else:
        url = '/'
    return redirect(url)


def poster(request, videoid):
    """Generate a still frame for a video (if needed) and
    generate a redirect to the static server for this frame"""

    video = get_object_or_404(GlossVideo, gloss_id=videoid)

    return redirect(video.poster_url())


def video(request, videoid):
    """Redirect to the video url for this videoid"""

    video = get_object_or_404(GlossVideo, gloss_id=videoid)

    return redirect(video)

def iframe(request, videoid):
    """Generate an iframe with a player for this video"""
    
    try:
        gloss = Gloss.objects.get(pk=videoid)
        glossvideo = gloss.get_video()
        
        videourl = glossvideo.get_absolute_url()
                
        posterurl = glossvideo.poster_url()
    except:
        gloss = None
        glossvideo = None
        videourl = None
        posterurl = None


    return render(request,"iframe.html",
                              {'videourl': videourl,
                               'posterurl': posterurl,
                               'aspectRatio': settings.VIDEO_ASPECT_RATIO})


def create_still_images(request):
    processed_videos = []
    for gloss in Gloss.objects.all():
        video_path = WRITABLE_FOLDER + gloss.get_video_path()
        if os.path.isfile(video_path.encode('UTF-8')):
            idgloss_prefix = gloss.idgloss[:2]
            (folder, basename) = os.path.split(video_path)
            generate_still_image(idgloss_prefix, folder + os.sep, basename)
            processed_videos.append(video_path)
    return HttpResponse('Processed videos: <br/>' + "<br/>".join(processed_videos))


from django.core.files.uploadedfile import UploadedFile
from django.forms.util import ValidationError
from django import forms
from django.conf import settings
import sys, os, time, signal
from subprocess import Popen, PIPE
from tempfile import mkstemp
from signbank.log import debug
import shutil, stat

from django.core.mail import mail_admins, EmailMessage
from signbank.video.convertvideo import convert_video

from logging import debug

class UploadedFLVFile(UploadedFile):
    """
    A file converted to FLV.
    """
    def __init__(self, name): 
        self.name = name
        self.fullname = name # needed because UploadedFile will clobber .name
        self.field_name = None
        self.content_type = 'video/flv'
        self.charset = None
        self.file = open(name)
    
    def read(self, *args):          return self.file.read(*args)
    def seek(self, *args):          return self.file.seek(*args)
    def tell(self, *args):          return self.file.tell(*args)
    def __iter__(self):             return iter(self.file)
    def readlines(self, size=None): return self.file.readlines(size)
    def xreadlines(self):           return self.file.xreadlines()

    
    def rename(self, location):
        """Rename (move) the file to a new location on disk"""
        
        #debug("moving %s to %s (%s)" % (self.fullname, location, self._name))
        # use fullname here because name has been clobbered by UploadedFile
        # need shutil.copy not os.rename because temp dir might be a different device
        source = self.fullname
        shutil.copy(source, location)
        # make sure they're readable by everyone
        os.chmod(location, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH )
        self.name = location
        # remove the original
        #os.unlink(source)
        
    def delete(self):
        """Remove the file"""
        #os.unlink(self.name)
        

class VideoUploadToFLVField(forms.FileField):
    """A custom form field that supports uploading video
    files and converting them to FLV (flash video) before 
    saving"""

    def __init__(self, geometry="300x240", prefix='upload', **kwargs):
        """
        Added fields:
            - geometry: specify the geometry of the final video, eg. "300x240"
            
        """

        super(VideoUploadToFLVField, self).__init__(**kwargs)
        self.geometry = geometry
        self.prefix = prefix


    def clean(self, data, initial=None):
        """Checks that the file is valid video and converts it to
        FLV format"""
        
        
        f = super(VideoUploadToFLVField, self).clean(data, initial)
        if f is None:
            return None
        elif not data and initial:
            return initial

        # We need the data to be in a real file for ffmpeg. 
        # either it's already written out to a tmp file or
        # we have to do it here
        
        if hasattr(data, 'temporary_file_path'):
            tmpname = data.temporary_file_path()
        else:
            # need to store in-memory data out to a temp file
            if settings.FILE_UPLOAD_TEMP_DIR:
                (tmp, tmpname) = mkstemp(prefix=self.prefix, 
                                         dir=settings.FILE_UPLOAD_TEMP_DIR)
            else:
                (tmp, tmpname) = mkstemp(prefix=self.prefix)

            
            for chunk in f.chunks():
                os.write(tmp,chunk)
            os.close(tmp)
            
        # construct an mp4 filename
        mp4file = tmpname+".mp4"
        # now do the conversion to mp4
        # will raise an error on failure 
        self.convert(tmpname, mp4file)
        # we want to return an UploadedFile obj representing
        # the flv file, not the original but I can't 
        # create one of those from an existing file
        # so I use my own wrapper class            
        debug("Converted to mp4: " + mp4file)

        #os.unlink(tmpname)
        return UploadedFLVFile(mp4file) 
    
    def convert(self, sourcefile, targetfile):
        """Convert a video to h264 format using the magic script"""
        
        if convert_video(sourcefile, targetfile):
            return True
        else:
            errormsg = "Video conversion failed"
            raise ValidationError(errormsg)


    def xconvert(self, sourcefile, targetfile):
        """Convert video to mp4 format"""

        errormsg = ""
        
        # ffmpeg command options:
        #  -y  answer yes to all queries
        #  -v -1 be less verbose
        # -i sourcefile   input file
        # -f flv  output format is flv
        # -an no audio in output
        # -s geometry set size of output
        #
        # new options for conversion to h264/mp4
        # ffmpeg -v -1 -i $1 -an -vcodec libx264 -vpre hq -crf 22 -threads 0 $1:r.mp4
        #
        ffmpeg = [settings.FFMPEG_PROGRAM, "-y", "-v", "-1", "-i", sourcefile, "-vcodec", "libx264", "-an", "-vpre", "hq", "-crf", "22", "-threads", "0", targetfile]
     
        debug(" ".join(ffmpeg))
        
        process =  Popen(ffmpeg, stdout=PIPE, stderr=PIPE)
        start = time.time()
        
        while process.poll() == None: 
            if time.time()-start > settings.FFMPEG_TIMEOUT:
                # we've gone over time, kill the process  
                os.kill(process.pid, signal.SIGKILL)
                debug("Killing ffmpeg process")
                errormsg = "Conversion of video took too long.  This site is only able to host relatively short videos."
        

        status = process.poll()
        #out,err = process.communicate()

        # Check if file exists and is > 0 Bytes
        try:
            s = os.stat(targetfile) 
            fsize = s.st_size
            if (fsize == 0):
                os.remove(targetfile)
                errormsg = "Conversion of video failed: please try to use a diffent format"
        except:
            errormsg = "Conversion of video failed: please try to use a different video format"
            
        if errormsg:
            # we have a conversion error
            # notify the admins, attaching the offending file
            msgtxt = "Error: %s\n\nCommand: %s\n\n" % (errormsg, " ".join(ffmpeg))
            
            message = EmailMessage("Video conversion failed on Auslan",
                                   msgtxt,
                                   to=[a[1] for a in settings.ADMINS])
            message.attach_file(sourcefile)
            message.send(fail_silently=False)
            
            
            # and raise a validation error for the caller
            raise ValidationError(errormsg)


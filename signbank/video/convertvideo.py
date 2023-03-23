#!/usr/bin/python

try:
    from django.conf import settings
    FFMPEG_PROGRAM = settings.FFMPEG_PROGRAM
    FFMPEG_OPTIONS = settings.FFMPEG_OPTIONS
except:
    FFMPEG_PROGRAM = "/usr/bin/ffmpeg"
    #FFMPEG_OPTIONS = ["-vcodec", "libx264", "-an", "-vpre", "hq", "-crf", "22", "-threads", "0"]
    FFMPEG_OPTIONS = ["-vcodec", "h264", "-an"]

import sys, os, time, signal, shutil
import ffmpeg
from subprocess import Popen, PIPE
import re
    
def parse_ffmpeg_output(text):
    """Get relevant info from the ffmpeg output"""

    ffmpeg_output_string = text
    # print('argument to parse_ffmpeg_output: ', ffmpeg_output_string)
    state = None
    result = {'input': '', 'output': ''}
    for line in ffmpeg_output_string.split(b'\n'):
        if line.startswith(b"Input"):
            state = "INPUT"
        elif line.startswith(b"Output"):
            state = "OUTPUT"
        elif line.startswith(b"Stream mapping:"):
            state = "OTHER"
        
        if state == "INPUT":
            result['input'] += line.decode('UTF-8') + "\n"

        if state == "OUTPUT":
            result['output'] += line.decode('UTF-8') + "\n"
            
    # check for video input format
    m = re.search("Video: ([^,]+),", result['input'])
    if m:
        result['inputvideoformat'] = m.groups()[0]
    else:
        result['inputvideoformat'] = 'unknown'
        
    return result
            
            
def frame_to_timecode(frame, fps):
    """Get timecode of a specific frame with fps"""

    hours = int(frame / (3600 * fps))
    minutes = int(frame / (60 * fps) % 60)
    seconds = int(frame / fps % 60)
    frem = int(frame % fps)
    return "{:02d}:{:02d}:{:02d}.{:02d}".format(hours, minutes, seconds, frem)


def get_middle_timecode(videofile):
    """Determine the timecode of the middle frame of a video"""

    p = ffmpeg.probe(videofile)
    video_stream = next((stream for stream in p['streams'] if stream['codec_type'] == 'video'), None)
    middle_frame = int(video_stream["nb_frames"]) // 2
    fps = eval(video_stream["r_frame_rate"])
    ss = frame_to_timecode(middle_frame, fps)
    return ss


def run_ffmpeg(sourcefile, targetfile, timeout=60, options=[]):
    """Run FFMPEG with some command options, returning the output"""

    errormsg = ""
    
    ffmpeg = [FFMPEG_PROGRAM, "-y", "-i", sourcefile]
    ffmpeg += options
    ffmpeg += [targetfile]

    process =  Popen(ffmpeg, stdout=PIPE, stderr=PIPE)
    start = time.time()
    
    while process.poll() == None: 
        if time.time()-start > timeout:
            # we've gone over time, kill the process  
            os.kill(process.pid, signal.SIGKILL)
            print("Killing ffmpeg process for", sourcefile)
            errormsg = "Conversion of video took too long.  This site is only able to host relatively short videos."
            return errormsg
        
    status = process.poll()
    out,err = process.communicate()
    
    # should check status
    
    # return the error output - messages from ffmpeg
    return err

def extract_frame(sourcefile, targetfile):
    """Extract a single frame from the source video and 
    write it to the target file"""
    
    options = ["-r", "1", "-f", "mjpeg"]
    
    err = run_ffmpeg(sourcefile, targetfile, options=options)


def probe_format(file):
    """Find the format of a video file via ffmpeg,
    return a format name, eg mpeg4, h264"""
    
    # for info, convert just one second to a null output format
    info_options = ["-f", "null", "-t", "1"]
    
    b = run_ffmpeg(file, "tmp", options=info_options)
    r = parse_ffmpeg_output(b)
     
    return r['inputvideoformat']



def convert_video(sourcefile, targetfile, force=False):
    """convert a video to h264 format
    if force=True, do the conversion even if the video is already
    h264 encoded, if False, then just copy the file in this case"""
    
    if not force:
        format = probe_format(sourcefile)
    else:
        format = 'force'
    
    if format == "h264":
        # just do a copy of the file
        shutil.copy(sourcefile, targetfile) 
    else: 
        # convert the video
        b = run_ffmpeg(sourcefile, targetfile, options=FFMPEG_OPTIONS)

    format = probe_format(targetfile)
    if format.startswith('h264'):
        # the output of ffmpeg includes extra information following h264, so only check the prefix
        return True
    else:
        return False
        
if __name__=='__main__':
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: convertvideo.py <sourcefile> <targetfile>")
        exit()
        
    sourcefile = sys.argv[1]
    targetfile = sys.argv[2]
    
    convert_video(sourcefile, targetfile)
        
    
        
        
        
    

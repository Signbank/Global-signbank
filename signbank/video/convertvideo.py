#!/usr/bin/python

try:
    from django.conf import settings
    FFMPEG_PROGRAM = settings.FFMPEG_PROGRAM
    FFMPEG_OPTIONS = settings.FFMPEG_OPTIONS
except KeyError:
    FFMPEG_PROGRAM = "/usr/bin/ffmpeg"
    # FFMPEG_OPTIONS = ["-vcodec", "libx264", "-an", "-vpre", "hq", "-crf", "22", "-threads", "0"]
    FFMPEG_OPTIONS = ["-vcodec", "h264", "-an"]

import sys
import os
import time
import signal
import shutil
import glob
import ffmpeg
from subprocess import Popen, PIPE
import re
import subprocess
from signbank.settings.server_specific import DEBUG_VIDEOS


def parse_ffmpeg_output(text):
    """Get relevant info from the ffmpeg output"""

    ffmpeg_output_string = text
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

    process = Popen(ffmpeg, stdout=PIPE, stderr=PIPE)
    start = time.time()
    
    while process.poll() is None:
        if time.time()-start > timeout:
            # we've gone over time, kill the process  
            os.kill(process.pid, signal.SIGKILL)
            print("Killing ffmpeg process for", sourcefile)
            errormsg = "Conversion of video took too long.  This site is only able to host relatively short videos."
            return errormsg
        
    status = process.poll()
    out, err = process.communicate()
    
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


def generate_image_sequence(sourcefile):
    basename, _ = os.path.splitext(sourcefile.path)
    temp_location_frames = os.path.join(settings.WRITABLE_FOLDER,
                                        settings.GLOSS_IMAGE_DIRECTORY, "signbank-thumbnail-frames")
    filename, ext = os.path.splitext(os.path.basename(sourcefile.name))
    filename = filename.replace(' ', '_')
    folder_name, _ = os.path.splitext(filename)
    temp_video_frames_folder = os.path.join(temp_location_frames, folder_name)
    # Create the necessary subfolder if needed
    if not os.path.isdir(temp_location_frames):
        os.mkdir(temp_location_frames)
    if not os.path.isdir(temp_video_frames_folder):
        os.mkdir(temp_video_frames_folder)
    else:
        # remove old files before generating again
        stills_pattern = temp_video_frames_folder + "/*.png"
        for f in glob.glob(stills_pattern):
            os.remove(f)
    (
        ffmpeg
        .input(sourcefile.path, ss=1)
        .filter('fps', fps=15, round='up')
        .output("%s/%s-%%04d.png" % (temp_video_frames_folder, folder_name), **{'qscale:v': 2})
        .run(quiet=True)
    )
    stills = []
    for filename in os.listdir(temp_video_frames_folder):
        still_path = os.path.join(temp_video_frames_folder, filename)
        stills.append(still_path)

    return stills


def remove_stills(sourcefile):
    basename, _ = os.path.splitext(sourcefile.path)
    temp_location_frames = os.path.join(settings.WRITABLE_FOLDER,
                                        settings.GLOSS_IMAGE_DIRECTORY, "signbank-thumbnail-frames")
    filename, ext = os.path.splitext(os.path.basename(sourcefile.name))
    filename = filename.replace(' ', '_')
    folder_name, _ = os.path.splitext(filename)
    temp_video_frames_folder = os.path.join(temp_location_frames, folder_name)
    # remove the temp files
    stills_pattern = temp_video_frames_folder+"/*.png"
    for f in glob.glob(stills_pattern):
        os.remove(f)


def make_thumbnail_video(sourcefile, targetfile):
    # this method is not called (need to move temp files to /tmp instead)
    # this function also works on source quicktime videos
    # the sourcefile needs to be a videofile
    basename, _ = os.path.splitext(sourcefile.path)
    temp_target = basename + '_small.mov'
    temp_location_frames = os.path.join(settings.TMP_DIR, "signbank-thumbnail-frames")
    filename, ext = os.path.splitext(os.path.basename(sourcefile.name))
    filename = filename.replace(' ', '_')
    folder_name, _ = os.path.splitext(filename)
    temp_video_frames_folder = os.path.join(temp_location_frames, folder_name)
    # Create the necessary subfolder if needed
    if not os.path.isdir(temp_location_frames):
        os.mkdir(temp_location_frames)
    if not os.path.isdir(temp_video_frames_folder):
        os.mkdir(temp_video_frames_folder)
    (
        ffmpeg
        .input(sourcefile.path)
        .filter('fps', fps=15, round='up')
        .filter('scale', -2, 180)
        .output("%s/%s-%%04d.png" % (temp_video_frames_folder, folder_name), **{'qscale:v': 2})
        .run(quiet=True)
    )
    image_files_path = os.path.join(temp_video_frames_folder, folder_name)
    (
        ffmpeg
        .input(temp_video_frames_folder+"/*.png", pattern_type='glob', framerate=15)
        .output(temp_target, vcodec='rawvideo')
        .run(quiet=True)
    )
    # convert the small video to mp4
    convert_video(temp_target, targetfile)

    # remove the temp files
    stills_pattern = temp_video_frames_folder+"/*.png"
    for f in glob.glob(stills_pattern):
        os.remove(f)
    os.remove(temp_target)


def video_file_type_extension(video_file_full_path):
    if not os.path.exists(video_file_full_path):
        return ".mp4"
    filetype_output = subprocess.run(["file", video_file_full_path], stdout=subprocess.PIPE)
    filetype = str(filetype_output.stdout)
    if 'MOV' in filetype:
        desired_video_extension = '.mov'
    elif 'M4V' in filetype:
        desired_video_extension = '.m4v'
    elif 'MP4' in filetype:
        desired_video_extension = '.mp4'
    elif 'Matroska' in filetype:
        desired_video_extension = '.webm'
    elif 'MKV' in filetype:
        desired_video_extension = '.mkv'
    elif 'MPEG-2' in filetype:
        desired_video_extension = '.m2v'
    else:
        if DEBUG_VIDEOS:
            print('video:admin:convertvideo:video_file_type_extension:file:UNKNOWN ', filetype)
        desired_video_extension = '.mp4'
    return desired_video_extension


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
    elif "h264" in format:
        # ffmpeg copy video channel to new file with .mp4 extension
        FFMPEG_COPY_OPTIONS = ["-c", "copy", "-an"]
        b = run_ffmpeg(sourcefile, targetfile, options=FFMPEG_COPY_OPTIONS)
    else: 
        # convert the video
        RAW_OPTIONS = ["-f", "rawvideo", "-vcodec", "h264"]
        # RAW_OPTIONS = ["-vcodec", "libx264", "-an"]
        print('convert small video: ', RAW_OPTIONS)
        b = run_ffmpeg(sourcefile, targetfile, options=RAW_OPTIONS)
        print(b)

    format = probe_format(targetfile)
    if format.startswith('h264'):
        # the output of ffmpeg includes extra information following h264, so only check the prefix
        return True
    else:
        return False


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print("Usage: convertvideo.py <sourcefile> <targetfile>")
        exit()
        
    sourcefile = sys.argv[1]
    targetfile = sys.argv[2]
    
    convert_video(sourcefile, targetfile)

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


def get_folder_name(gloss):
    gloss_video_filename = gloss.idgloss + '-' + str(gloss.id)
    filename = gloss_video_filename.replace(' ', '_')
    folder_name = filename.replace('.', '-')
    return folder_name


def generate_image_sequence(gloss, sourcefile):

    temp_location_frames = os.path.join(settings.WRITABLE_FOLDER,
                                        settings.GLOSS_IMAGE_DIRECTORY, "signbank-thumbnail-frames")
    folder_name = get_folder_name(gloss)
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
        .input(sourcefile.path, ss=0.5)
        .filter('fps', fps=25, round='up')
        .output("%s/%s-%%04d.png" % (temp_video_frames_folder, folder_name), **{'qscale:v': 2})
        .run(quiet=True)
    )
    stills = []
    for filename in os.listdir(temp_video_frames_folder):
        still_path = os.path.join(temp_video_frames_folder, filename)
        stills.append(still_path)

    return stills


def remove_stills(gloss):
    temp_location_frames = os.path.join(settings.WRITABLE_FOLDER,
                                        settings.GLOSS_IMAGE_DIRECTORY, "signbank-thumbnail-frames")
    folder_name = get_folder_name(gloss)
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
    okay = convert_video(temp_target, targetfile)

    # remove the temp files
    stills_pattern = temp_video_frames_folder+"/*.png"
    for f in glob.glob(stills_pattern):
        os.remove(f)
    os.remove(temp_target)


# Documentation only: works on Ubuntu and matches older files/code.
ACCEPTABLE_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm', '.m4v', '.mkv', '.m2v']


def extension_on_filename(filename):
    # used to retrieve a video type file extension from a filename where there is no file
    filename_with_extension = os.path.basename(filename)
    filename_without_extension, ext = os.path.splitext(os.path.basename(filename))

    if ext in ACCEPTABLE_VIDEO_EXTENSIONS:
        return ext

    m = re.search(r".+-(\d+)\.(mp4|m4v|mov|webm|mkv|m2v)\.(bak\d+)$", filename_with_extension)
    if m:
        return '.'+m.group(2)
    m = re.search(r".+-(\d+)\.(mp4|m4v|mov|webm|mkv|m2v)\.(bak\d+)$", filename_without_extension)
    if m:
        return '.'+m.group(2)
    # Default if no file exists and the filename is invalid, allows to work on dev servers.
    return '.mp4'


def detect_video_file_extension(file_path):
    filename, extension = os.path.splitext(file_path)
    if not os.path.exists(file_path):
        return extension
    filetype_output = subprocess.run(["file", "-b", file_path], stdout=subprocess.PIPE)
    filetype = str(filetype_output.stdout)
    if 'MP4' in filetype:
        video_extension = '.mp4'
    elif 'MOV' in filetype:
        video_extension = '.mov'
    elif 'M4V' in filetype:
        video_extension = '.m4v'
    elif 'Matroska' in filetype:
        video_extension = '.webm'
    elif 'MKV' in filetype:
        video_extension = '.mkv'
    elif 'MPEG-2' in filetype:
        video_extension = '.m2v'
    else:
        video_extension = extension
    return video_extension


def video_file_type_extension(video_file_full_path):

    if not video_file_full_path or 'glossvideo' not in str(video_file_full_path):
        return ''

    if not os.path.exists(video_file_full_path):
        return extension_on_filename(video_file_full_path)

    filetype_output = subprocess.run(["file", "-b", video_file_full_path], stdout=subprocess.PIPE)
    filetype = str(filetype_output.stdout)
    if 'MP4' in filetype:
        desired_video_extension = '.mp4'
    elif 'MOV' in filetype:
        desired_video_extension = '.mov'
    elif 'M4V' in filetype:
        desired_video_extension = '.m4v'
    elif 'Matroska' in filetype:
        desired_video_extension = '.webm'
    elif 'MKV' in filetype:
        desired_video_extension = '.mkv'
    elif 'MPEG-2' in filetype:
        desired_video_extension = '.m2v'
    else:
        # no match found, print something to the log and just keep using what's on the filename
        if DEBUG_VIDEOS:
            print('video:admin:convertvideo:video_file_type_extension:file:UNKNOWN ', filetype)
        desired_video_extension = extension_on_filename(video_file_full_path)
    return desired_video_extension


def convert_video(sourcefile, targetfile):
    """convert a video to h264 format
    if force=True, do the conversion even if the video is already
    h264 encoded, if False, then just copy the file in this case"""

    if not os.path.exists(sourcefile):
        return False

    basename, source_file_extension = os.path.splitext(sourcefile)

    video_format_extension = detect_video_file_extension(sourcefile)
    file_with_extension_matching_video_type = f'{basename}{video_format_extension}'

    if source_file_extension == '.mp4' and video_format_extension == ".mp4":
        return True

    input_file = file_with_extension_matching_video_type if source_file_extension != video_format_extension else sourcefile
    if input_file != sourcefile:
        # the file extension of the source does not match the type of video, rename it for conversion
        os.rename(sourcefile, input_file)

    result = subprocess.run(["ffmpeg", "-i", input_file, targetfile])
    return result.returncode == 0


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print("Usage: convertvideo.py <sourcefile> <targetfile>")
        exit()
        
    sourcefile = sys.argv[1]
    targetfile = sys.argv[2]
    
    okay = convert_video(sourcefile, targetfile)

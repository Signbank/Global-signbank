import sys
import os
import time
import signal
import glob
import ffmpeg
import re
import logging

import magic

from signbank.settings.server_specific import DEBUG_VIDEOS

try:
    from django.conf import settings
    FFMPEG_PROGRAM = settings.FFMPEG_PROGRAM
except KeyError:
    FFMPEG_PROGRAM = "/usr/bin/ffmpeg"


logger = logging.getLogger(__name__)


thumbnail_frames_dir = "signbank-thumbnail-frames"


def frame_to_timecode(frame, fps):
    """Get timecode of a specific frame with fps"""
    hours = int(frame / (3600 * fps))
    minutes = int(frame / (60 * fps) % 60)
    seconds = int(frame / fps % 60)
    frem = int(frame % fps)
    return "{:02d}:{:02d}:{:02d}.{:02d}".format(hours, minutes, seconds, frem)


def get_middle_timecode(videofile):
    """Determine the timecode of the middle frame of a video"""
    ffprobe = ffmpeg.probe(videofile)
    video_stream = next((stream for stream in ffprobe['streams'] if stream['codec_type'] == 'video'), None)
    middle_frame = int(video_stream["nb_frames"]) // 2
    fps = eval(video_stream["r_frame_rate"])
    ss = frame_to_timecode(middle_frame, fps)
    return ss


def extract_frame(sourcefile, targetfile):
    """Extract a single frame from the source video and write it to the target file"""
    ffmpeg.input(sourcefile).output(targetfile, r=1, f="mjpeg").run(overwrite_output=True, quiet=True)


def get_folder_name(gloss):
    return (f'{gloss.idgloss}-{gloss.id}'
            .replace(' ', '_')
            .replace('.', '-'))


def generate_image_sequence(gloss, sourcefile):
    temp_location_frames = os.path.join(settings.WRITABLE_FOLDER, settings.GLOSS_IMAGE_DIRECTORY, thumbnail_frames_dir)
    if not os.path.isdir(temp_location_frames):
        os.mkdir(temp_location_frames)

    folder_name = get_folder_name(gloss)
    temp_video_frames_folder = os.path.join(temp_location_frames, folder_name)
    if not os.path.isdir(temp_video_frames_folder):
        os.mkdir(temp_video_frames_folder)
    else:
        for file in glob.glob(temp_video_frames_folder + "/*.png"):
            os.remove(file)

    (ffmpeg.input(sourcefile.path, ss=0.5)
           .filter('fps', fps=25, round='up')
           .output("%s/%s-%%04d.png" % (temp_video_frames_folder, folder_name), **{'qscale:v': 2})
           .run(quiet=True))

    return [os.path.join(temp_video_frames_folder, filename) for filename in os.listdir(temp_video_frames_folder)]


def remove_stills(gloss):
    temp_location_frames = os.path.join(settings.WRITABLE_FOLDER, settings.GLOSS_IMAGE_DIRECTORY, thumbnail_frames_dir)
    temp_video_frames_folder = os.path.join(temp_location_frames, get_folder_name(gloss))
    for f in glob.glob(temp_video_frames_folder+"/*.png"):
        os.remove(f)


# Documentation only: works on Ubuntu and matches older files/code.
FILETYPE_EXTENSION_MAPPING = {
    'MP4': '.mp4',
    'MOV': '.mov',
    'M4V': '.m4v',
    'Matroska': 'webm',
    'MKV': '.mkv',
    'MPEG-2': '.m2v'
}
ACCEPTABLE_VIDEO_EXTENSIONS = list(FILETYPE_EXTENSION_MAPPING.values())


def extension_on_filename(filename):
    filename_with_extension = os.path.basename(filename)
    filename_without_extension, ext = os.path.splitext(os.path.basename(filename))

    if ext in ACCEPTABLE_VIDEO_EXTENSIONS:
        return ext

    extension_pattern = '|'.join(ACCEPTABLE_VIDEO_EXTENSIONS)
    pattern = rf".+-(\d+)({extension_pattern})\.(bak\d+)$"
    for name in [filename_with_extension, filename_without_extension]:
        if m := re.search(pattern, name):
            return m.group(2)

    return '.mp4'


def get_extension_from_type(file_path):
    filetype = magic.from_file(file_path)
    for type in FILETYPE_EXTENSION_MAPPING:
        if type in filetype:
            return FILETYPE_EXTENSION_MAPPING[type]

    if DEBUG_VIDEOS:
        logger.info(f"video:admin:convertvideo:get_extension_from_type  :file:UNKNOWN {filetype}")
    return None


def detect_video_file_extension(file_path):
    filename, extension = os.path.splitext(file_path)
    if not os.path.exists(file_path):
        return extension

    if extension_from_type := get_extension_from_type(file_path):
        return extension_from_type

    return extension


def video_file_type_extension(video_file_full_path):
    if not video_file_full_path or 'glossvideo' not in str(video_file_full_path):
        return ''

    if not os.path.exists(video_file_full_path):
        return extension_on_filename(video_file_full_path)

    if extension_from_type := get_extension_from_type(video_file_full_path):
        return extension_from_type

    return extension_on_filename(video_file_full_path)


def convert_video(sourcefile, targetfile):
    """convert a video to h264 format"""
    if not os.path.exists(sourcefile):
        return False

    basename, source_file_extension = os.path.splitext(sourcefile)
    video_format_extension = detect_video_file_extension(sourcefile)
    if source_file_extension == '.mp4' and video_format_extension == ".mp4":
        return True

    file_with_extension_matching_video_type = f'{basename}{video_format_extension}'
    input_file = file_with_extension_matching_video_type if source_file_extension != video_format_extension else sourcefile
    if input_file != sourcefile:
        os.rename(sourcefile, input_file)

    try:
        ffmpeg.input(input_file).output(targetfile).run(quiet=True)
        return True
    except ffmpeg.Error as e:
        logger.error(e)
        return False


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: convertvideo.py <sourcefile> <targetfile>")
        exit()
        
    sourcefile = sys.argv[1]
    targetfile = sys.argv[2]
    
    okay = convert_video(sourcefile, targetfile)

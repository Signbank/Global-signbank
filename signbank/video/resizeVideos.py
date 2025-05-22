#!/usr/bin/python

"""
This script will resize video dimensions and delete frames from beginning and end.
"""

from __future__ import print_function

import getopt
import json
import os
import sys
from subprocess import Popen, PIPE
from fractions import Fraction

__author__ = "Micha Hulsbosch"
__date__ = "August 2016"

class VideoResizer:
    """
    Resizes the dimension and duration of a video.
    """

    def __init__(self, video_files, ffmpeg_cmd="ffmpeg", resize_scale=-1, frames_begin=0, frames_end=-1):
        """
        :param video_files: a list of video file names
        :param ffmpeg_cmd: the ffmpeg command (on Ubuntu it is 'avconv')
        :param resize_scale: the heigth of the resized video
        :param frames_begin: the number of frames to delete from the beginning
        :param frames_end: the number of frames to delete from the end
        :return:
        """
        self.video_files = video_files
        self.ffmpeg_cmd = ffmpeg_cmd
        self.resize_scale = resize_scale
        self.frames_begin = frames_begin
        self.frames_end = frames_end

    def run(self, dry_run=False):
        """
        Runs the resizing process for the list of video files
        :param dry_run: if true, do not run the actual resizing, only output the used command
        :return:
        """
        for video_file in self.video_files:
            print("Video file: " + video_file)
            (frame_rate, duration) = self.extract_video_properties(video_file)
            frame_duration = 1/frame_rate
            begin_time = self.frames_begin * frame_duration
            end_time = duration - self.frames_end * frame_duration
            self.resize_video(video_file, begin_time, end_time, dry_run)

    def extract_video_properties(self, video_file):
        """
        Extracts video properties frame rate and duration
        :param video_file:
        :return:
        """
        probe_cmd = self.ffmpeg_cmd[0:2] + "probe"
        cmd = [probe_cmd, "-of", "json", "-show_streams", video_file]

        with open(os.devnull, 'w') as devnull:
            p = Popen(cmd, stdout=PIPE, stderr=devnull)
            properties = json.loads(p.communicate()[0].decode())
            for stream in properties["streams"]:
                if stream["codec_type"] == "video":
                    frame_rate = float(Fraction(stream["avg_frame_rate"]))
                    duration = float(stream["duration"])
                    return frame_rate, duration

    def resize_video(self, video_file, begin_time, end_time, dry_run=False):
        """
        Resizes a video file using an ffmpeg command
        :param video_file: the video to resize
        :param begin_time: the begin cut
        :param end_time: the end cut
        :param dry_run: if true, do not run the actual resizing, only output the used command
        :return:
        """
        # scale_formula = "scale='trunc(iw*max(1,sar)/%f)*2':'trunc(ih*max(1,1/sar)/%f)*2'" \
        #                     % (1/self.resize_scale * 2, 1/self.resize_scale * 2)
        scale_formula = "scale=(trunc((iw/(ih/%f))/2+0.5))*2:%f" % (self.resize_scale, self.resize_scale)
        path, ext = os.path.splitext(video_file)
        output_file = path + "_small" + ext

        cmd = [self.ffmpeg_cmd,
               "-v", "quiet",
               "-i", video_file,
               "-ss", str(begin_time),
               "-t", str(end_time - begin_time),
               "-filter:v", scale_formula,
               "-strict", "experimental",
               "-y",
               output_file]
        print(" ".join(cmd))
        if not dry_run:
            Popen(cmd)

if __name__ == "__main__":
    usage = "Usage: \n" + sys.argv[0] + \
            " -c <ffmpeg command if not 'ffmpeg'> -s <height in pixels> -b <begin frame index>" + \
            " -e <end frame index> [-d] <file|directory ...>"

    opt_list, file_list = getopt.getopt(sys.argv[1:], 'c:s:b:e:dh')

    ffmpeg_command = "ffmpeg"
    resize_scale = -1
    frames_begin = 0
    frames_end = -1
    dry_run = False

    for opt in opt_list:
        if opt[0] == '-c':
            ffmpeg_command = opt[1]
        if opt[0] == '-s':
            resize_scale = int(opt[1])
        if opt[0] == '-b':
            frames_begin = int(opt[1])
        if opt[0] == '-e':
            frames_end = int(opt[1])
        if opt[0] == '-d':
            dry_run = True
        if opt[0] == '-h':
            print(usage)
            exit(0)

    resizer = VideoResizer(file_list, ffmpeg_command, resize_scale, frames_begin, frames_end)
    resizer.run(dry_run)
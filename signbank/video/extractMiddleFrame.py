#!/usr/bin/python

"""
This script will resize video dimensions and delete frames from beginning and end.
"""

from __future__ import print_function

import getopt
from urllib.parse import urlparse
import os
import sys
from shutil import copyfile, rmtree
from subprocess import Popen
from math import floor

__author__ = "Micha Hulsbosch"
__date__ = "October 2016"


class MiddleFrameExtracter:
    """


    """

    def __init__(self, video_files, output_dir=None, ffmpeg_cmd="ffmpeg", delete_frames=True):
        """
        :param video_files: a list of video file names
        :param ffmpeg_cmd: the ffmpeg command (on Ubuntu it is 'avconv')
        :return:
        """
        self.video_files = video_files
        self.ffmpeg_cmd = ffmpeg_cmd
        self.delete_frames = delete_frames

        if output_dir:
            self.output_dir = output_dir.rstrip(os.sep)
        if not os.path.isdir(self.output_dir):
            os.makedirs(self.output_dir, 0o750)

    def run(self, dry_run=False):
        """
        Runs the extraction process for the list of video files
        :param dry_run: if true, do not run the actual resizing, only output the used command
        :return:
        """
        middle_frame_dirs = []
        for video_file in self.video_files:
            print("Video file: " + video_file, file=sys.stderr)
            dirs = self.create_dirs(video_file)
            middle_frame_dirs.append(dirs[1])
            self.extract_frames(video_file, dry_run, dirs)
            self.create_video_stills(video_file, dry_run, dirs)
            if self.delete_frames:
                rmtree(dirs[0])

        return middle_frame_dirs

    def create_dirs(self, video_file):
        new_dirs = []
        for dir_name in ["all", "middle"]:
            new_dir = self.output_dir + os.sep + \
                      os.path.basename(video_file) + "-frames" + os.sep + dir_name
            if not os.path.isdir(new_dir):
                os.makedirs(new_dir, 0o750)
            new_dirs.append(new_dir)

        return new_dirs

    def extract_frames(self, video_file, dry_run, dirs):
        scale_formula = "scale='iw*max(1,sar)':'ih*max(1,1/sar)'"
        output_file = dirs[0] + os.sep + "frame-%5d.png"

        cmd = [
            self.ffmpeg_cmd,
            "-v", "quiet",
            "-i", video_file,
            "-filter:v", scale_formula,
            output_file
        ]

        print(" ".join(cmd), file=sys.stderr)
        if not dry_run:
            p = Popen(cmd)
            p.wait()

    def create_video_stills(self, video_file, dry_run, dirs):
        """
        Creates the video still:
        1. The middle frame
        2. a 320x180 version of that middle frame
        :param video_file:
        :param dry_run:
        :param dirs:
        :return:
        """
        frames_dir = dirs[0]
        frames = sorted(os.listdir(frames_dir))
        if len(frames) != 0:
            middle_frame_index = int(floor(len(frames)/2))
            middle_frame = frames[middle_frame_index]
            video_base_name = os.path.basename(video_file)
            video_name = os.path.splitext(video_base_name)[0]
            video_still = dirs[1] + os.sep + video_name + '.png'
            if not dry_run:
                copyfile(frames_dir + os.sep + middle_frame, video_still)

            # Create the 320x180 version
            cmd = [
                "convert",
                video_still,
                "-resize", "x180",
                dirs[1] + os.sep + video_name + '_320x180.png'
            ]
            print(" ".join(cmd), file=sys.stderr)
            if not dry_run:
                p = Popen(cmd)
                p.wait()

if __name__ == "__main__":
    usage = "Usage: \n" + sys.argv[0] + \
            " -c <ffmpeg command if not 'ffmpeg'>" + \
            " -o <output directory>" + \
            " [-r]" + \
            " [-d]" + \
            " <file|directory ...>"

    opt_list, file_list = getopt.getopt(sys.argv[1:], 'c:o:drh')

    ffmpeg_command = "ffmpeg"
    output_dir = ""
    delete_frames = True
    dry_run = False

    for opt in opt_list:
        if opt[0] == '-c':
            ffmpeg_command = opt[1]
        if opt[0] == '-o':
            output_dir = opt[1]
        if opt[0] == '-r':
            delete_frames = False
        if opt[0] == '-d':
            dry_run = True
        if opt[0] == '-h':
            print(usage)
            exit(0)

    resizer = MiddleFrameExtracter(file_list, output_dir, ffmpeg_command, delete_frames)
    print(", ".join(resizer.run(dry_run)))
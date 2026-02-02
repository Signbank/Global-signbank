import os
import re
import shutil

from signbank.settings.server_specific import (WRITABLE_FOLDER, DEBUG_VIDEOS, DELETED_FILES_FOLDER)


def filename_matches_nme(filename):
    filename_without_extension, ext = os.path.splitext(os.path.basename(filename))
    return re.search(r".+-(\d+)_(nme_\d+|nme_\d+_left|nme_\d+_right|nme_\d+_center)$", filename_without_extension)


def filename_matches_nme_backup(filename):
    filename_with_extension = os.path.basename(filename)
    return re.search(r".+-(\d+)_(nme_\d+|nme_\d+_left|nme_\d+_right|nme_\d+_center)\.(mp4|m4v|mov|webm|mkv|m2v)\.(bak\d+)$", filename_with_extension)


def filename_matches_perspective(filename):
    filename_without_extension, ext = os.path.splitext(os.path.basename(filename))
    return re.search(r".+-(\d+)_(left|right|nme_\d+_left|nme_\d+_right)$", filename_without_extension)


def filename_matches_perspective_backup(filename):
    filename_with_extension = os.path.basename(filename)
    return re.search(r".+-(\d+)_(left|right|nme_\d+_left|nme_\d+_right)\.(mp4|m4v|mov|webm|mkv|m2v)\.(bak\d+)$", filename_with_extension)


def filename_matches_video(filename):
    filename_without_extension, ext = os.path.splitext(os.path.basename(filename))
    return re.search(r".+-(\d+)$", filename_without_extension)


def filename_matches_backup_video(filename):
    filename_with_extension = os.path.basename(filename)
    return re.search(r".+-(\d+)\.(mp4|m4v|mov|webm|mkv|m2v)\.(bak\d+)$", filename_with_extension)


def flattened_video_path(relative_path):
    """
    This constructs the filename to be used in the DELETED_FILES_FOLDER
    Take apart the gloss video relative path
    If this succeeds, prefix the filename with the dataset-specific components
    Otherwise just return the filename
    """
    relative_path_folders, filename = os.path.split(relative_path)
    m = re.search(r"^glossvideo/(.+)/(..)$", relative_path_folders)
    if m:
        dataset_folder = m.group(1)
        two_char_folder = m.group(2)
        return f"{dataset_folder}_{two_char_folder}_{filename}"
    return filename


def move_file_to_prullenmand(filepath, relative_path):
    deleted_file_name = flattened_video_path(relative_path)
    deleted_destination = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER, deleted_file_name)
    destination_dir = os.path.join(WRITABLE_FOLDER, DELETED_FILES_FOLDER)
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
    try:
        shutil.move(str(filepath), str(deleted_destination))
        if DEBUG_VIDEOS:
            print('video:models:move_file_to_prullenmand:shutil.move: ', filepath,
                  deleted_destination)
    except (OSError, PermissionError) as e:
        if DEBUG_VIDEOS:
            print('video:models:move_file_to_prullenmand:shutil.move: ', filepath,
                  deleted_destination)
            print('video:models:move_file_to_prullenmand:shutil.move: ', e)
        # if the file cannot be moved, just delete it
        os.remove(str(filepath))

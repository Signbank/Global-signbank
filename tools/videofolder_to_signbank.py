import sys
import os

#==========================
# Constants
#==========================

sb_video_folder = '/www/signbank/live/writable/glossvideo/';

#==========================
# Functions
#==========================

def video_to_signbank(source_folder,filename):
        
    destination_folder = sb_video_folder+filename[:2]+'/';

    #Create the necessary subfolder if needed
    if not os.path.isdir(destination_folder):
        os.mkdir(destination_folder);

    #Move the file
    os.rename(source_folder+filename,destination_folder+filename);

#==========================
# The standalone script
#==========================

if __name__ == '__main__':

    #Parse arguments
    try:
        folderpath = sys.argv[1];
    except IndexError:
        print('Syntax: python videofolder_to_signbank.py path/to/videofolder');
        exit();

    #Add a slash if needed
    if folderpath[-1] != '/':
        folderpath += '/';

    for filename in os.listdir(folderpath):

        #Skip all non-videos
        if not '.mp4' in filename:
            continue;

        print('Moving '+filename);
        video_to_signbank(folderpath,filename);

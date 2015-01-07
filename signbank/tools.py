import sys
import os

#==========================
# Constants
#==========================

root = '/var/www2/signbank/live/';
sb_video_folder = root+'writable/glossvideo/';

#==========================
# Functions
#==========================

def video_to_signbank(source_folder,gloss,extension):
        
	#Add a dot before the extension if needed
	if extension[0] != '.':
		extension = '.' + extension;

	#Figure out some names
	annotation_id = gloss.annotation_idgloss;
	pk = str(gloss.pk);
	destination_folder = sb_video_folder+annotation_id[:2]+'/';

    #Create the necessary subfolder if needed
	if not os.path.isdir(destination_folder):
		os.mkdir(destination_folder);

    #Move the file
	source = source_folder+annotation_id+extension;
	goal = destination_folder+annotation_id+'-'+pk+extension;
	os.rename(source,goal);

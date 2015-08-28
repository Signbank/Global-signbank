DEBUG = False
TEMPLATE_DEBUG = DEBUG
EMAIL_HOST =  "smtp.webfaction.com"
EMAIL_HOST_USER = "stevecassidy"
EMAIL_HOST_PASSWORD = "k399doopl"

DATABASE_ENGINE = 'mysql'          
DATABASE_NAME = 'stevecassidy_aln'          
DATABASE_USER = 'stevecassidy_aln'            
DATABASE_PASSWORD = 'pigeon59'        
DATABASE_HOST = ''             
DATABASE_PORT = '' 

# Absolute path to the directory that holds media. 
MEDIA_ROOT = '/home/stevecassidy/webapps/auslanstatic/auslan-video/'
# URL that handles the media served from MEDIA_ROOT. 
MEDIA_URL = 'http://www.auslan.org.au/media/auslan-video/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
ADMIN_MEDIA_PREFIX = 'http://djangomedia.stevecassidy.webfactional.com/'

# Ditto for static files from the Auslan site (css, etc) with trailing slash 
AUSLAN_STATIC_PREFIX = "http://www.auslan.org.au/media/auslan-static/"

# location of ffmpeg, used to convert uploaded videos
FFMPEG_PROGRAM = "/home/stevecassidy/bin/ffmpeg.sh"
FFMPEG_TIMEOUT = 60
FFMPEG_OPTIONS = ["-vcodec", "libx264", "-an", "-vpre", "hq", "-crf", "22", "-threads", "0"]

TEMPLATE_DIRS = (
    '/home/stevecassidy/webapps/auslan/auslan/templates'
)

LOG_FILENAME = "/home/stevecassidy/logs/user/auslan-debug.log"

FILE_UPLOAD_TEMP_DIR = "/home/stevecassidy/videoupload/"


#This is small script that you can run during development
#It monitors the current directory, and touches the wsgi file when it finds a change
#It depends on the pyinotify package

import signbank.settings.server_specific
import pyinotify
import urllib

wm = pyinotify.WatchManager()  # Watch Manager
mask = pyinotify.IN_MODIFY  # watched events

class EventHandler(pyinotify.ProcessEvent):
    def process_IN_MODIFY(self,filename):
        print('File modified '+str(filename))

        try:
            urllib.urlopen(settings.server_specific.URL+'reload_signbank/').read()
        except urllib.HTTPError:
            pass

print('Starting to monitor')

handler = EventHandler()
notifier = pyinotify.Notifier(wm, handler)
wdd = wm.add_watch(signbank.settings.server_specific.BASE_DIR+'signbank/', mask, rec=True)

notifier.loop()
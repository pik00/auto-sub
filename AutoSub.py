

import sys
import getopt
import os
import signal
import time

#signal.signal(signal.SIGTERM, autosub.AutoSub.signal_handler)

help_message = '''
Usage:
    -h (--help)     Prints this message
    -c (--config=)  Forces AutoSub.py to use a configfile other than ./config.properties
    -d (--daemon)   Run AutoSub in the background
    -l (--nolaunch) Stop AutoSub from launching a webbrowser
    
Example:
    python AutoSub.py
    python AutoSub.py -d
    python AutoSub.py -d -l
    python AutoSub.py -c/home/user/config.properties
    python AutoSub.py --config=/home/user/config.properties
    python AutoSub.py --config=/home/user/config.properties --daemon
    
'''

# TODO: comments in everyfile

class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

def main(argv=None):
    
    import autosub
    
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args= getopt.getopt(argv[1:], "hc:dl", ["help","config=","daemon","nolaunch"])
        except getopt.error, msg:
            raise Usage(msg)
    
        # option processing
        for option, value in opts:
            if option in ("-h", "--help"):
                raise Usage(help_message)
            if option in ("-c", "--config"):
                autosub.CONFIGFILE = value
            if option in ("-l", "--nolaunch"):
                autosub.LAUNCHBROWSER = False
            if option in ("-d", "--daemon"):
                if sys.platform == "win32":
                    print "ERROR: No support for daemon mode in Windows"
                    # TODO: Service support for Windows
                else:
                    autosub.DAEMON = True
    
    except Usage, err:
        print >> sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg)
        print >> sys.stderr, "\t for help use --help"
        return 2
    
    #load configuration
    if os.path.isfile('config.properties.dev'):
        autosub.CONFIGFILE='config.properties.dev'
    print "AutoSub: Initializing variables and loading config"
    autosub.Initialize()
    
    import autosub.AutoSub
    
    signal.signal(signal.SIGINT, autosub.AutoSub.signal_handler)
    
    if autosub.DAEMON==True:
        autosub.AutoSub.daemon()
    
    import autosub.Db
    
    #make sure that sqlite database is loaded after you demonize 
    if autosub.Db.initDatabase():
        print "AutoSub: Database created"
    
    #change to the new work directory
    if os.path.exists(autosub.PATH):
        os.chdir(autosub.PATH)
    else:
        print "AutoSub: ERROR PATH does not exist, check config."
        os._exit(1)
    
    print "AutoSub: Changing output to log. Bye!"
    log = autosub.initLogging(autosub.LOGFILE)
    
    log.info("AutoSub: Starting threads")
    autosub.AutoSub.start()
    
    if autosub.LAUNCHBROWSER:
        autosub.AutoSub.launchBrowser()
    
    log.info("AutoSub: threads started, going into a loop to keep the main thread going")
    
    while True:
        time.sleep(1)
if __name__ == "__main__":
    sys.exit(main())

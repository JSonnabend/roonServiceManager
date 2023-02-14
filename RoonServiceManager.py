#0.1.12

import sys
# path to roonapi folder
sys.path.append('\\pyRoon\\pyRoonLib\\roonapi')
import roonapi, discovery, constants
import webserver
import time, os, ctypes
import json
# import socket
import threading
# from constants import LOGGER
import logging
from logging.handlers import RotatingFileHandler

pingcount = 0
settings = None
dataFolder = None
dataFile = None
appinfo = {
    "extension_id": "sonnabend.roon.servicemanager",
    "display_name": "Roon Service Manager",
    "display_version": "alpha",
    "publisher": "sonnabend",
    "email": "",
}
roon = None
logger = logging.getLogger('roonservicemanager')
# configure file logging
file_handler = RotatingFileHandler('roonservicemanager.log', maxBytes=1e5, backupCount=5)
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(fmt='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
# configure console logging
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)



def main():
    try:
        global roon
        global settings
        global logger
        loadSettings()
        logLevelString = settings.get("log_level", "INFO").upper()
        if logLevelString == "DEBUG" or inDebugger():
            level = logging.DEBUG
        elif logLevelString == "INFO":
            level = logging.INFO
        elif logLevelString == "WARNING":
            level = logging.WARNING
        elif logLevelString == "ERROR":
            level = logging.ERROR
        elif logLevelString == "CRITICAL":
            level = logging.CRITICAL
        logger.setLevel(level)

        # authorize if necessary
        try:
            if settings["core_id"].strip() == "" or settings["token"] == "":
                authorize()
        except:
            authorize()
        # connect to Roon core
        roon = connect(settings["core_id"], settings["token"])
        settings["core_id"] = roon.core_id
        settings["token"] = roon.token
        settings["max_allowed_response_time"] = settings.get("max_allowed_response_time", 15)
        settings["roon_service_name"] = settings.get("roon_service_name", "RoonServer")
        settings["ping_delay"] = settings.get("ping_delay", 60)
        ''' subscribe to status notifications '''
        # roon.register_state_callback(state_change_callback)
        ''' subscribe to queue notifications '''
        # roon.register_queue_callback(queue_change_callback, "16017ce7f01013a8a2d865696c6e5bd8d542")
        ''' register volume control '''
        # hostname = socket.gethostname()
        # roon.register_volume_control("1", hostname, volume_control_callback, 0, "incremental")

        '''start http server'''
        settings["webserver_port"] = settings.get("webserver_port", 18007)
        thread = threading.Thread(target=webserver.run, kwargs={'port':settings["webserver_port"]})
        thread.start()

        # '''start pinger'''
        # thread2 = threading.Thread(target=ping_core)
        # thread2.start()
        while True:
            ping_core()
            logger.debug("waiting %s seconds until next ping." % settings["ping_delay"])
            time.sleep(settings["ping_delay"])

    finally:
        #finally, save settings
        if not (settings is None):
            saveSettings()

def connect(core_id, token):
    global logger
    logger.info("in connect\n  core_id: %s\n  token: %s" % (core_id,token))
    global appinfo
    try:
        discover = discovery.RoonDiscovery(core_id, dataFolder)
        logger.info("discover object: %s" % discover)
        server = discover.first()
        logger.info("server object: %s:%s" % (server[0], server[1]))
        roon = roonapi.RoonApi(appinfo, token, server[0], server[1], True)
        logger.info("connected to roon core: %s" % roon)
        return roon
    except Exception as e:
        raise e
        return None
    finally:
        discover.stop()

def authorize():
    global logger
    logger.info("authorizing")
    global appinfo
    global settings

    logger.info("discovering servers")
    discover = discovery.RoonDiscovery(None)
    servers = discover.all()
    logger.info("discover: %s\nservers: %s" % (discover, servers))

    logger.info("Shutdown discovery")
    discover.stop()

    logger.info("Found the following servers")
    logger.info(servers)
    apis = [roonapi.RoonApi(appinfo, None, server[0], server[1], False) for server in servers]

    auth_api = []
    while len(auth_api) == 0:
        logger.info("Waiting for authorisation")
        time.sleep(1)
        auth_api = [api for api in apis if api.token is not None]

    api = auth_api[0]

    logger.info("Got authorisation")
    logger.info("\t\thost ip: " + api.host)
    logger.info("\t\tcore name: " + api.core_name)
    logger.info("\t\tcore id: " + api.core_id)
    logger.info("\t\ttoken: " + api.token)
    # This is what we need to reconnect
    settings["core_id"] = api.core_id
    settings["token"] = api.token

    logger.info("leaving authorize with settings: %s" % settings)

    logger.info("Shutdown apis")
    for api in apis:
        api.stop()

def queue_change_callback(queuedata):
    global logger
    global roon
    """Call when something changes in roon queue."""
    print("\n")
    logger.info("queue_change_callback queuedata: %s" % (queuedata))

def state_change_callback(event, changed_ids):
    global roon
    """Call when something changes in roon."""
    print("\n")
    logger.info("state_change_callback event:%s changed_ids: %s" % (event, changed_ids))
    for zone_id in changed_ids:
        zone = roon.zones[zone_id]
        logger.info("zone_id:%s zone_info: %s" % (zone_id, zone))

def volume_control_callback(control_key, event, value):
   pass

def ping_core():
    global pingcount
    global logger
    global settings
    global roon
    responseTime = "not calculated"
    try:
        pingcount += 1
        coreString = "'%s' at %s:%s" % (roon.core_name, roon.host, roon.port)
        logger.debug("pinging core %s. (%s)" % (coreString, pingcount))
        start = time.time()
        response = roon.browse_browse(json.loads('{"hierarchy":"browse"}'))
        end = time.time()
        responseTime = round(end - start)
        logger.debug("response time %s." % responseTime)
    except:
        logger.info("error pinging core %s. response time %s. restarting core now." % (coreString, responseTime))
        responseTime = 1e6
    if responseTime > settings["max_allowed_response_time"]:
        restart_core_service(settings["roon_service_name"])
    pass

def restart_core_service(serviceName):
    global logger
    if isAdmin():
        try:
            logger.info("stopping %s" % serviceName)
            commandString = "net stop \"%s\""  % serviceName
            os.system(commandString)
            time.sleep(1)
            commandString = "net start \"%s\""  % serviceName
            os.system(commandString)
        except:
            logger.info("error restarting %s. check service status manually." % serviceName)
            return
    else:
        logger.info('application must be running as admin to start/stop Windows services')
    pass


def loadSettings():
    global logger
    global settings
    global dataFile
    global dataFolder
    logger.info("running from %s" % __file__)
    if inDebugger(): #("_" in __file__): # running in temp directory, so not from PyCharm
        dataFolder = os.path.dirname(__file__)
    else:
        dataFolder = os.path.join(os.getenv('APPDATA'), 'pyRoonServiceManager')  #os.path.abspath(os.path.dirname(__file__))
    dataFile = os.path.join(dataFolder , 'settings.dat')
    logger.info("using dataFile: %s" % dataFile)
    if not os.path.isfile(dataFile):
        f = open(dataFile, 'a').close()
    try:
        f = open(dataFile, 'r')
        settings = json.load(f)
    except:
        settings = json.loads('{}')
    f.close()
    return settings

def saveSettings():
    global logger
    global settings
    data = json.dumps(settings, indent=4)
    if (not data  == '{}') and (os.path.isfile(dataFile)):
        f = open(dataFile, 'w')
        f.write(data)
        f.close()

def isAdmin():
    global logger
    try:
        is_admin = (os.getuid() == 0)
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    return is_admin

def inDebugger():
    return not ("_" in __file__)

if __name__ == "__main__":
    main()
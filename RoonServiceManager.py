

import sys
# path to roonapi folder
sys.path.append('\\pyRoon\\pyRoonLib\\roonapi')
import roonapi, discovery, constants
import time, datetime, os, ctypes
import json
import threading
# from constants import LOGGER
import logging
from logging.handlers import RotatingFileHandler

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
    logger.info('running main')
    appinfo = {
        "extension_id": "sonnabend.roon.servicemanager",
        "display_name": "Roon Service Manager",
        "display_version": "alpha 1.2",
        "publisher": "sonnabend",
        "email": "",
    }
    logger.info('createing RoonServiceManager with appinfo: %s' % appinfo)
    roonServiceManager = RoonServiceManager()
    roonServiceManager.appinfo = appinfo
    logger.info('calling roonServiceManager.start()')
    roonServiceManager.start()

class RoonServiceManager:
    global logger
    _logger = logger
    _pingcount = 0
    _lastping = None
    _settings = None
    _dataFolder = None
    _dataFile = None
    _appinfo = {
        "extension_id": "",
        "display_name": "",
        "display_version": "",
        "publisher": "",
        "email": "",
    }
    _roon = None


    @property
    def settings(self):
        return self._settings
    @property
    def appinfo(self):
        return self._appinfo

    @appinfo.setter
    def appinfo(self, value):
        self._appinfo = value

    @property
    def roon(self):
        # result = json.dumps(self._roon)
        return self._roon

    @property
    def pingcount(self):
        return self._pingcount

    @property
    def lastping(self):
        return self._lastping

    def __init__(self, appinfo=""):
        self._appinfo = appinfo
        self.loadSettings()
        logLevelString = self._settings.get("log_level", "INFO").upper()
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
        self._logger.setLevel(level)

    def start(self):
        try:
            # authorize if necessary
            try:
                if self._settings["core_id"].strip() == "" or self._settings["token"] == "":
                    self.authorize()
            except:
                self.authorize()
            # connect to Roon core
            self._roon = self.connect()
            self._settings["core_id"] = self._roon.core_id
            self._settings["token"] = self._roon.token
            self._settings["max_allowed_response_time"] = self._settings.get("max_allowed_response_time", 15)
            self._settings["roon_service_name"] = self._settings.get("roon_service_name", "RoonServer")
            self._settings["ping_delay"] = self._settings.get("ping_delay", 60)
            self._settings["roon_service_name"] = self._settings.get("roon_service_name", "RoonServer")
            ''' subscribe to status notifications '''
            # self._roon.register_state_callback(self._state_change_callback)
            ''' subscribe to queue notifications '''
            # self._roon.register_queue_callback(self._queue_change_callback, "16017ce7f01013a8a2d865696c6e5bd8d542")
            ''' register volume control '''
            # import socket
            # hostname = socket.gethostname()
            # self._roon.register_volume_control("1", hostname, self._volume_control_callback, 0, "incremental")

            '''start http server'''
            import webserver
            self._settings["webserver_port"] = self._settings.get("webserver_port", 18007)
            webserver.roonservicemanager = self
            thread = threading.Thread(target=webserver.run, kwargs={'port':self._settings["webserver_port"]})
            thread.start()
            '''run main loop'''
            while True:
                self.ping_core()
                logger.debug("waiting %s seconds until next ping." % self._settings["ping_delay"])
                time.sleep(self._settings["ping_delay"])
        finally:
            #finally, save settings
            thread.join()
            if not (self._settings is None):
                self.saveSettings()
                
    def connect(self):
        self._logger.info("in connect\n  core_id: %s\n  token: %s" % (self._settings["core_id"],self._settings["token"]))
        try:
            discover = discovery.RoonDiscovery(self._settings["core_id"], self._dataFolder)
            self._logger.info("discover object: %s" % discover)
            server = discover.first()
            self._logger.info("server object: %s:%s" % (server[0], server[1]))
            roon = roonapi.RoonApi(self._appinfo, self._settings["token"], server[0], server[1], True)
            self._logger.info("connected to roon core: %s" % roon)
            return roon
        except Exception as e:
            raise e
            return None
        finally:
            discover.stop()

    def authorize(self):
        self._logger.info("authorizing")

        self._logger.info("discovering servers")
        discover = discovery.RoonDiscovery(None)
        servers = discover.all()
        self._logger.info("discover: %s\nservers: %s" % (discover, servers))

        self._logger.info("Shutdown discovery")
        discover.stop()

        self._logger.info("Found the following servers")
        self._logger.info(servers)
        apis = [roonapi.RoonApi(self._appinfo, None, server[0], server[1], False) for server in servers]

        auth_api = []
        while len(auth_api) == 0:
            self._logger.info("Waiting for authorisation")
            time.sleep(1)
            auth_api = [api for api in apis if api.token is not None]

        api = auth_api[0]

        self._logger.info("Got authorisation")
        self._logger.info("\t\thost ip: " + api.host)
        self._logger.info("\t\tcore name: " + api.core_name)
        self._logger.info("\t\tcore id: " + api.core_id)
        self._logger.info("\t\ttoken: " + api.token)
        # This is what we need to reconnect
        self.settings["core_id"] = api.core_id
        self.settings["token"] = api.token

        self._logger.info("leaving authorize with settings: %s" % settings)

        self._logger.info("Shutdown apis")
        for api in apis:
            api.stop()

    def _queue_change_callback(self, queuedata):
        """Call when something changes in roon queue."""
        print("\n")
        self._logger.info("queue_change_callback queuedata: %s" % (queuedata))

    def _state_change_callback(self, event, changed_ids):
        """Call when something changes in roon."""
        print("\n")
        self._logger.info("state_change_callback event:%s changed_ids: %s" % (event, changed_ids))
        for zone_id in changed_ids:
            zone = self._roon.zones[zone_id]
            self._logger.info("zone_id:%s zone_info: %s" % (zone_id, zone))

    def _volume_control_callback(self, control_key, event, value):
        print("\n")
        self._logger.info("volume_control_callback control_key: %s  event: %s  value: %s" % (control_key, event, value))

    def ping_core(self):
        responseTime = "not calculated"
        try:
            self._pingcount += 1
            coreString = "'%s' at %s:%s" % (self._roon.core_name, self._roon.host, self._roon.port)
            self._logger.debug("pinging core %s. (%s)" % (coreString, self._pingcount))
            # start = time.time()
            start = datetime.datetime.now()
            response = self._roon.browse_browse(json.loads('{"hierarchy":"browse"}'))
            self._logger.debug("response %s." % response)
            end = datetime.datetime.now()
            responseTime = end.timestamp() - start.timestamp()
            self._logger.debug("response time %s." % responseTime)
        except:
            self._logger.info("error pinging core %s. response time %s. restarting core now." % (coreString, responseTime))
            responseTime = 1e6
        finally:
            pingTime = start.__str__()
            self._lastping = {'pingcount':self._pingcount,'pingtime':pingTime,'responseTime':responseTime, 'response': response}
        if responseTime > self._settings["max_allowed_response_time"]:
            self.restart_core_service()

    def restart_core_service(self):
        try:
            if isAdmin():
                try:
                    self._logger.info(f"stopping {self._settings['roon_service_name']}")
                    from subprocess import run
                    commandString = f"net stop \"{self._settings['roon_service_name']}\""
                    #CompletedProcess(args='net stop "None"', returncode=2, stdout=b'', stderr=b'The service name is invalid.\r\n\r\nMore help is available by typing NET HELPMSG 2185.\r\n\r\n')
                    processResult = run(commandString, capture_output=True)
                    stderr = processResult.stderr.decode('utf-8')
                    stdout = processResult.stdout.decode('utf-8')
                    result = processResult.stdout if stdout.strip() != "" else stderr
                    result = str(result, 'utf-8')
                    self._logger.info(f"{result}")
                    # os.system(commandString)
                    time.sleep(1)
                    commandString = f"net start \"{self._settings['roon_service_name']}\""
                    processResult = run(commandString, capture_output=True)
                    stderr = processResult.stderr.decode("utf-8")
                    stdout = processResult.stdout.decode("utf-8")
                    # result = result + "\n"
                    nextresult = processResult.stdout if stdout.strip() != "" else stderr
                    nextresult = str(nextresult, 'utf-8')
                    result = result + "\n" + nextresult
                    self._logger.info(f"{result}")
                    # result = os.system(commandString)
                except:
                    self._logger.info(f"error restarting {self._settings['roon_service_name']}. check service status manually.")
                    result = f"error restarting {self._settings['roon_service_name']}. check service status manually."
            else:
                self._logger.info('application must be running as admin to start/stop Windows services')
                result = 'application must be running as admin to start/stop Windows services'
        finally:
            return result

    def loadSettings(self):
        self._logger.info("running from %s" % __file__)
        if inDebugger(): #("_" in __file__): # running in temp directory, so not from PyCharm
            self._dataFolder = os.path.dirname(__file__)
        else:
            self._dataFolder = os.path.join(os.getenv('APPDATA'), 'pyRoonServiceManager')  #os.path.abspath(os.path.dirname(__file__))
        self._dataFile = os.path.join(self._dataFolder , 'settings.dat')
        self._logger.info("using dataFile: %s" % self._dataFile)
        if not os.path.isfile(self._dataFile):
            f = open(self._dataFile, 'a').close()
        try:
            f = open(self._dataFile, 'r')
            self._settings = json.load(f)
        except:
            self._settings = json.loads('{}')
        f.close()
        return self._settings

    def saveSettings(self):
        data = json.dumps(self._settings, indent=4)
        if (not data  == '{}') and (os.path.isfile(self._dataFile)):
            f = open(self._dataFile, 'w')
            f.write(data)
            f.close()

    def getLog(self):
        try:
            logfile = open('roonservicemanager.log', 'r')
            logcontents = logfile.read()
            return logcontents
        finally:
            logfile.close()

def isAdmin():
    global logger
    try:
        is_admin = (os.getuid() == 0)
    except AttributeError:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    return is_admin

def inDebugger():
    return not ("_" in __file__)

def test():
    appinfo = {
        "extension_id": "sonnabend.roon.servicemanager",
        "display_name": "Roon Service Manager",
        "display_version": "alpha 1.2",
        "publisher": "sonnabend",
        "email": "",
    }
    roonServiceManager = RoonServiceManager(appinfo)
    roonServiceManager.start()
    roonServiceManager.restart_core_service()


if __name__ == "__main__":
    if inDebugger():
        # test()
        main()
    else:
        main()
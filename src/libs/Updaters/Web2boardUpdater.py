import logging
import os
import platform
import shutil
import subprocess
import sys
import time

from libs import utils
from libs.Config import Config
from libs.Decorators.Asynchronous import asynchronous
from libs.Downloader import Downloader
from libs.PathsManager import PathsManager as pm
from libs.Updaters.Updater import Updater, VersionInfo
from libs.Version import Version


class Web2BoardUpdater(Updater):
    __globalWeb2BoardUpdater = None
    log = logging.getLogger(__name__)

    def __init__(self, copyOriginName=None, copyNewName=None):
        Updater.__init__(self)
        self.currentVersionInfo = VersionInfo(Version.web2board)
        self.destinationPath = pm.ORIGINAL_PATH
        self.name = "Web2BoardUpdater"

        copyPath = pm.COPY_PATH
        if copyOriginName is None:
            copyOriginName = "web2board" + utils.get_executable_extension()
        if copyNewName is None:
            copyNewName = "web2board_copy" + utils.get_executable_extension()
        self.__executableCopyOriginalName = os.path.join(copyPath, copyOriginName)
        self.__executableCopyNewName = os.path.relpath(os.path.join(copyPath, copyNewName), os.getcwd())

        self.downloader = Downloader(refreshTime=1)

    def _areWeMissingLibraries(self):
        return False

    def getDownloadUrl(self, onlineVersionInfo=None):
        if onlineVersionInfo is None:
            onlineVersionInfo = self.downloadOnlineVersionInfo()

        args = dict(arch=64 if utils.is64bits() else 32,
                    os=platform.system(),
                    version=onlineVersionInfo.version)

        return Config.download_url_template.format(**args)

    @asynchronous()
    def downloadVersion(self, version, infoCallback=None, endCallback=None):
        confirmationPath = pm.get_dst_path_for_update(version) + ".confirm"
        zipDstPath = pm.get_dst_path_for_update(version) + ".zip"
        if not os.path.exists(confirmationPath):
            url = self.getDownloadUrl(VersionInfo(version))
            self.downloader.download(url, dst=zipDstPath, info_callback=infoCallback, end_callback=endCallback).result()
            utils.extract_zip(zipDstPath, pm.get_dst_path_for_update(version))
            os.remove(zipDstPath)
            with open(confirmationPath, "w"):
                pass
        else:
            endCallback(None)

    def makeAnAuxiliaryCopy(self):
        try:
            self.log.info("Creating an auxiliary copy of the program in {}".format(pm.COPY_PATH))
            if os.path.exists(pm.COPY_PATH):
                shutil.rmtree(pm.COPY_PATH)
            shutil.copytree(pm.MAIN_PATH, pm.COPY_PATH)
            os.rename(self.__executableCopyOriginalName, self.__executableCopyNewName)
        except:
            self.log.critical("Upload process finished due to a problem in the uploader", exc_info=1)

    def runAuxiliaryCopy(self, version):
        try:
            self.log.info("Running auxiliary copy")
            command = '"{0}" --update2version {1} &'.format(self.__executableCopyNewName, version)
            self.log.info("executing command: {}".format(command))
            logging.getLogger().removeHandler(logging.getLogger().handlers[1])
            os.popen(command)
            self.log.info("waiting to be killed")
            time.sleep(10)
            raise Exception("Program not ended after calling copy")
        except:
            self.log.critical("Upload process finished due to a problem in the uploader", exc_info=1)

    def update(self, versionPath):
        try:
            if pm.MAIN_PATH != pm.COPY_PATH:
                raise Exception("Unable to update, we are in the original version")
            self.log.info("updating in process")
            self.log.debug("killing original web2board")
            utils.kill_process("web2board")

            if os.path.exists(pm.ORIGINAL_PATH):
                self.log.info("removing original files")
                utils.rmtree(pm.ORIGINAL_PATH)
                self.log.info("removed original files")
            else:
                os.makedirs(pm.ORIGINAL_PATH)
            utils.copytree(versionPath, pm.ORIGINAL_PATH)
            os.remove(versionPath + ".confirm")
            self.log.debug("removing old version...")
            shutil.rmtree(versionPath)
            self.log.debug("removed old version")

            self.log.info("running new version")
            originalExePath = os.path.join(pm.ORIGINAL_PATH, "web2board" + utils.get_executable_extension())
            self.log.info(originalExePath)
            subprocess.call(['chmod', '0777', originalExePath])
            command = '"{0}" &'.format(originalExePath)
            os.popen(command)
        except:
            self.log.critical("Error updating", exc_info=1)
        finally:
            sys.exit(1)


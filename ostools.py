import os, sys
import platform
from PyQt5.QtCore import QStandardPaths

def isOSX():
    return sys.platform == "darwin"

def isWin32():
    return sys.platform == "win32"

def isLinux():
    return sys.platform.startswith("linux")

def isOSXBundle():
    return isOSX() and (os.path.abspath('.').find(".app") != -1)

def isOSXLeopard():
    return isOSX() and platform.mac_ver()[0].startswith("10.5")

def osVer():
    if isWin32():
        return " ".join(platform.win32_ver())
    elif isOSX():
        ver = platform.mac_ver();
        return " ".join((ver[0], " (", ver[2], ")"))
    elif isLinux():
        return " ".join(platform.linux_distribution())

def getDataDir():
    # Temporary fix for non-ascii usernames
    # If username has non-ascii characters, just store userdata
    # in the Pesterchum install directory (like before)
    # TODO: fix error if standardLocations is not what we expect
    try:
        
        if isOSX():
            return os.path.join(QStandardPaths.standardLocations(QStandardPaths.DataLocation)[0], "OSFC/")
        elif isLinux():
            return os.path.join(QStandardPaths.standardLocations(QStandardPaths.HomeLocation)[0], ".osfc/")
        else:
            return os.path.join(QStandardPaths.standardLocations(QStandardPaths.DataLocation)[0], "osfc/")
    except UnicodeDecodeError:
        return ''

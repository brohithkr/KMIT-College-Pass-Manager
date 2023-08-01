import requests
from configparser import ConfigParser
from sys import executable, argv, exit
from PyQt5 import QtWidgets, QtGui
from ServerUI import *
from MainWin import *
from os.path import dirname, abspath, join as joinpath, isfile
from os import remove as deleteFile
from platform import system
from threadingwithretval import ThreadWithReturnValue

BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

DATA_DIR = joinpath(dirname(abspath(__file__)), "data")

def checkInternet(url: str = "http://example.com") -> bool:
    try: requests.get(url, timeout=5)
    except (requests.ConnectionError, requests.Timeout): return False
    else: return True

if __name__ == "__main__":
    internetChecker = ThreadWithReturnValue(target=checkInternet)

    ostype = system()
    iconext = "png"

    if ostype == "Windows":
        # Windows Taskbar icon fix
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("KMIT.Passes.Generator.1")
        iconext = "ico"
    elif ostype == "Darwin": iconext = "icns"

    preconfigured_login: bool = False
    cfg = ConfigParser()
    if isfile(f'{BASE_DIR}/data/.config.ini'):
        cfg.read(f"{BASE_DIR}/data/.config.ini")
        sections = cfg.sections()
        if "Login" in sections:
            preconfigured_login = True
            UID, PWD = cfg["Login"]['uid'], cfg["Login"]["pwd"]

    app = QtWidgets.QApplication(argv)
    win = MainWindow()
    win.setWindowIcon(QtGui.QIcon(f"{DATA_DIR}/kmit.{iconext}"))

    if not internetChecker.join(): 
        QtWidgets.QMessageBox.critical(win, "KMIT Pass Generator: Error!", "Internet not connected.\nTry again later.")
        exit()
    del internetChecker

    def saveCFG():
        cfg = ConfigParser()
        UID, PWD = srvrdlg.getInputs()
        cfg["Login"] = {"uid": UID, "pwd": PWD}
        with open(f"{BASE_DIR}/data/.config.ini", 'w') as cfgfile:
            cfg.write(cfgfile)

    srvrhandler = ServerThreadHandler()
    srvrdlg = ServerDialog(win, cfg["Login"] if preconfigured_login else None, srvrhandler)
    srvrthread = QtCore.QThread()
    srvrhandler.moveToThread(srvrthread)
    srvrthread.started.connect(lambda: srvrhandler.login(*srvrdlg.getInputs()) \
                                     if preconfigured_login else srvrdlg.exec())
    srvrthread.started.connect(lambda: win.setWindowTitle("KMIT Fest Pass Generator: Logging in")\
                               and win.setDisabled(True))
    srvrhandler.error.connect(srvrdlg.error)
    srvrhandler.success.connect(srvrdlg.success)
    srvrdlg.accepted.connect(lambda: srvrhandler.login(*srvrdlg.getInputs()))
    srvrhandler.crash.connect(srvrdlg.crash)
    srvrhandler.success.connect(lambda: win._setLoginCreds(*srvrdlg.getInputs()))
    srvrhandler.success.connect(srvrthread.quit)
    srvrthread.finished.connect(srvrhandler.deleteLater)
    srvrthread.finished.connect(srvrthread.deleteLater)
    srvrhandler.success.connect(lambda: win.status.setText("Waiting for Data..."))
    srvrhandler.success.connect(lambda: win.setWindowTitle("KMIT Fest Pass Generator"))
    srvrhandler.success.connect(lambda: win.setDisabled(False))
    srvrhandler.success.connect(saveCFG) 
    
    srvrthread.start()

    win.show()

    if not preconfigured_login: 
        win.savecfg.connect(lambda persist: deleteFile(f"{BASE_DIR}/data/.config.ini")
                            if not persist else None) 

    exit(app.exec())


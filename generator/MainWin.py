from os.path import dirname, abspath, isfile, join as joinpath
from re import fullmatch
from base64 import b64decode as b64d
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSlot 
from PyQt5.uic import loadUi
from configparser import ConfigParser
import sys, requests

BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

DATA_DIR = joinpath(dirname(abspath(__file__)), "data")

pre_configured_server: bool = False
cfg = ConfigParser()
if isfile(f'{BASE_DIR}/data/.config.ini'):
    cfg.read(f"{BASE_DIR}/data/.config.ini")
    sections = cfg.sections()
    if "Login" in sections:
        pre_configured_server = True
        UID, PWD = cfg["Login"]['uid'], cfg["Login"]["pwd"]

class MainWindow(QtWidgets.QMainWindow):
    savecfg = QtCore.pyqtSignal(bool)
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        loadUi(f"{DATA_DIR}/design.ui", self)
        self._SetPASSimg()
        self._connectSignalsSlots()
        self.status = QtWidgets.QLabel()
        self.status.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        self.status.setStyleSheet("padding-right: 15px; padding-bottom: 3px")
        self.statusbar.addWidget(self.status, 1)
        self.statusbar.setSizeGripEnabled(False)
        self.Reason.setDisabled(True)

    def _SetPASSimg(self, img: str | bytes | None = None, B64: bool = False) -> None:
        self.passScene = QtWidgets.QGraphicsScene()
        if type(img) == bytes or B64:
            PASSimg = QtGui.QImage.fromData(b64d(img), 'PNG')
            PASSimgbox = QtWidgets.QGraphicsPixmapItem()
            PASSimgbox.setPixmap(QtGui.QPixmap.fromImage(PASSimg).scaled(600, 380))
            self.passScene.addItem(PASSimgbox)
        elif not B64:
            if img==None: img = "Enter Data"
            self.passScene.addText(img)

        self.Pass.setScene(self.passScene)
        self.Pass.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def closeEvent(self, e):
        if not pre_configured_server:
            res = QtWidgets.QMessageBox.question(self, "Save Login info?", "Do you want to save Login info for future?",
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if res == QtWidgets.QMessageBox.Yes: self.savecfg.emit(True)
            else: self.savecfg.emit(False)
        e.accept()

    @pyqtSlot(int)
    def comboBoxHandler(self, selectedOption: int):
        if selectedOption == 1: # Lunch Pass (Monthly)
            self.Reason.setPlaceholderText("Reason for leave. (N/A)") 
            self.Reason.setDisabled(True)
        elif selectedOption == 0: # Gate Pass (One Time)
            self.Reason.setEnabled(True) 
            self.Reason.setPlaceholderText("Reason for leave.")

    def _connectSignalsSlots(self) -> None:
        self.rno.returnPressed.connect(lambda: self.rno.setText(self.rno.text().upper()))
        self.rno.returnPressed.connect(lambda: self.PassType.setFocus())
        self.PassType.currentIndexChanged.connect(self.comboBoxHandler)
        self.Send.setAutoDefault(True)
        self.actionSend.triggered.connect(lambda: self.rno.setText(self.rno.text().upper()))
        self.Reason.returnPressed.connect(self.actionSend.trigger)
        self.actionSend.triggered.connect(self._preSend)

    def _clear(self) -> None:
        self.PassType.setCurrentIndex(-1)
        self.Send.setDisabled(False)
        self.rno.clear()
        self.Reason.clear()
        self._SetPASSimg()
        self.status.setText("Waiting for data...")
        self.rno.setFocus()

    def _setLoginCreds(self, UID, PWD):
        self.UID, self.PWD = UID, PWD

    def _getAuth(self):
        from ServerUI import ServerDialog, ServerThreadHandler
        self.auth = False
        srvrhandler = ServerThreadHandler()
        srvrdlg = ServerDialog(self, {"uid": self.UID, "pwd": ""}, srvrhandler, True)
        srvrthread = QtCore.QThread()
        srvrhandler.moveToThread(srvrthread)
        srvrthread.started.connect(srvrdlg.exec)
        srvrthread.started.connect(lambda: self.status.setText("Authenticating..."))
        srvrthread.started.connect(lambda: self.setDisabled(True))
        srvrhandler.error.connect(srvrdlg.error)
        srvrhandler.success.connect(srvrdlg.success)
        srvrdlg.invalid.connect(lambda: QtWidgets.QMessageBox.critical(self, "Attention!", "Unauthorised Access.")\
                                        and self._clear())
        srvrdlg.accepted.connect(lambda: srvrhandler.login(*srvrdlg.getInputs()))
        srvrhandler.crash.connect(srvrdlg.crash)
        srvrthread.finished.connect(srvrhandler.deleteLater)
        srvrthread.finished.connect(srvrthread.deleteLater)
        srvrhandler.success.connect(lambda: self.setDisabled(False))
        srvrthread.start()            

    def _preSend(self):
        from ServerUI import SERVERURL

        self.status.setText("Processing data...")
        self.Send.setDisabled(True)
        rno, reason = self.rno.text(), self.Reason.text()

        if rno == '' or (reason == '' and self.PassType.currentIndex == 0):
            QtWidgets.QMessageBox.information(self, "Empty Data", "Please fill out all the fields")
            self.Send.setDisabled(False)
            return
        elif not fullmatch(r'2\dBD1A\d{2}[A-HJ-NP-RT-Z0-9]{2}', rno): 
            self.status.setText("Invalid Roll No.")
            QtWidgets.QMessageBox.critical(self, "Error!", "Invalid Roll No. " + rno)
            self.Send.setDisabled(False)
            return
        
        self._sendPass()

    def _sendPass(self):        
        from ServerUI import SERVERURL
        from PassQRFetcher import PassFetcher

        self.status.setText("Working...")
        
        thread = QtCore.QThread()
        sender = PassFetcher(self.rno.text(), self.PassType.currentIndex())
        sender.moveToThread(thread)
        thread.started.connect(sender.fetchPass)
        sender.status.connect(self._setStatus)
        sender.Pass.connect(lambda img: self._SetPASSimg(img, True))
        sender.finished.connect(thread.quit)
        sender.finished.connect(self._clear)
        # thread.finished.connect(thread.deleteLater)
        # thread.finished.connect(sender.deleteLater)
        thread.start()

    @pyqtSlot(str)
    def _setStatus(self, status):
        self.status.setText(status)
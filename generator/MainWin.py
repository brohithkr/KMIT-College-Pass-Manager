from os.path import dirname, abspath, isfile, join as joinpath
from re import fullmatch
from base64 import b64decode as b64d
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import pyqtSlot 
from PyQt5.uic import loadUi
from configparser import ConfigParser
import sys

BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

DATA_DIR = joinpath(dirname(abspath(__file__)), "data")

preconfigured_login: bool = False
cfg = ConfigParser()
if isfile(f'{BASE_DIR}/data/.config.ini'):
    cfg.read(f"{BASE_DIR}/data/.config.ini")
    sections = cfg.sections()
    if "Login" in sections:
        preconfigured_login = True

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

    @pyqtSlot(bytes)
    def _SetPASSimg(self, img: bytes | None = None) -> None:
        passScene = QtWidgets.QGraphicsScene()
        if img == None:
            passScene.addText("Enter Data")
        else:
            PASSimg = QtGui.QImage.fromData(b64d(img), 'PNG')
            PASSimgbox = QtWidgets.QGraphicsPixmapItem()
            PASSimgbox.setPixmap(QtGui.QPixmap.fromImage(PASSimg).scaled(400, 300))
            passScene.addItem(PASSimgbox)
        self.Pass.setScene(passScene)
        self.Pass.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

    def closeEvent(self, e):
        if not preconfigured_login:
            res = QtWidgets.QMessageBox.question(self, "Save Login info?", "Do you want to save Login info for future?",
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if res == QtWidgets.QMessageBox.Yes: self.savecfg.emit(True)
            else: self.savecfg.emit(False)
        e.accept()

    @pyqtSlot(int)
    def comboBoxHandler(self, selectedOption: int):
        if selectedOption == 1: # Lunch Pass (Daily)
            self.Reason.setPlaceholderText("Reason for leave. (N/A)") 
            self.Reason.setDisabled(True)
        elif selectedOption == 0: # Gate Pass (SingleTime)
            self.Reason.setEnabled(True) 
            self.Reason.setPlaceholderText("Reason for leave.")

    def _connectSignalsSlots(self) -> None:
        self.rno.returnPressed.connect(lambda: self.rno.setText(self.rno.text().upper()))
        self.rno.returnPressed.connect(lambda: self.PassType.setFocus())
        self.PassType.currentIndexChanged.connect(self.comboBoxHandler)
        self.Send.setAutoDefault(True)
        self.actionSend.triggered.connect(lambda: self.rno.setText(self.rno.text().upper()))
        self.Reason.returnPressed.connect(self.actionSend.trigger)
        self.actionSend.triggered.connect(lambda: self._preSend() if self.Send.isEnabled() else None)

    def _clear(self, clearPass = True) -> None:
        self.PassType.setCurrentIndex(-1)
        self.Send.setDisabled(False)
        self.rno.clear()
        self.Reason.clear()
        self.status.setText("Waiting for data...")
        self.rno.setFocus()
        if clearPass: self._SetPASSimg(None)

    def resetThreads(self):
        self.thread = None
        self.sender = None

    def _setLoginCreds(self, UID, PWD):
        self.UID, self.PWD = UID, PWD

    def _preSend(self):
        self._clear()
        self.status.setText("Processing data...")
        self.Send.setDisabled(True)
        rno, reason = self.rno.text(), self.Reason.text()

        if rno == '' or (reason == '' and self.PassType.currentIndex != 1):
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
        from srvrcfg import SERVERURL
        from PassQRFetcher import PassFetcher

        self.status.setText("Working...")
        
        self.thread = QtCore.QThread()
        self.sender = PassFetcher(self.rno.text(), self.PassType.currentIndex())
        self.sender.moveToThread(self.thread)
        self.thread.started.connect(self.sender.run)
        self.sender.status.connect(self._setStatus)
        self.sender.generatedPass.connect(self._SetPASSimg)
        self.sender.mailRes.connect(self._mailResHandler)
        self.sender.finished.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.sender.deleteLater)
        self.thread.destroyed.connect(self.resetThreads)
        self.thread.start()

    @pyqtSlot(int)
    def _mailResHandler(self, status: int):
        if status == 401:
            QtWidgets.QMessageBox.critical(self, "Error!", "Unauthorised Access.")
        elif status == 406:
            QtWidgets.QMessageBox.critical(self, "Error!", "Sending E-Mail Failed.")
            self._clear(False)
        elif status == 200:
            QtWidgets.QMessageBox.information(self, "Success!", "E-Mail Sent successfully.")
            self._clear()

    @pyqtSlot(str)
    def _setStatus(self, status):
        self.status.setText(status)
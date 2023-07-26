from PyQt5 import QtCore
from PassUtil import *


class PassFetcher(QtCore.QObject):
    status = QtCore.pyqtSignal(str)
    Pass = QtCore.pyqtSignal(bytes)
    finished = QtCore.pyqtSignal()
    def __init__(self, rno, passType):
        super().__init__(None)
        self.rno, self.passType = rno, "monthly" if passType==1 else "daily"
        if self.passType == None:
            self.error.emit("Invalid Pass Type")

    def fetchPass(self):
        self.status.emit("Fetch QR code...")
        qrB64 = fetchQR(self.rno, self.passType)

        self.status.emit("Generating Pass...")
        passB64 = genPass(qrB64, self.passType)
        self.Pass.emit(passB64)

    def sendPass(self):
        self.status.emit("Sending Pass via email...")
        retVal = sendMail(self.rno, self.passType)
        self.result.emit(str(retVal))
        self.finished.emit()

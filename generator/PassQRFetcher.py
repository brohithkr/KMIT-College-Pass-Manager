from PyQt5 import QtCore
from PassUtil import *

class PassFetcher(QtCore.QObject):
    status = QtCore.pyqtSignal(str)
    generatedPass = QtCore.pyqtSignal(bytes)
    finished = QtCore.pyqtSignal()
    def __init__(self, rno, passType):
        super().__init__(None)
        self.rno, self.passType = rno, "daily" if passType==1 else "single-use"
        if self.passType == None:
            self.error.emit("Invalid Pass Type")

    def run(self):
        self.fetchPass()
        # self.sendPass()
        self.finished.emit()
        print("done")

    def fetchPass(self):
        self.status.emit("Fetch QR code...")
        qr_data = fetchQR(self.rno, self.passType)

        self.status.emit("Generating Pass...")
        passB64 = genPass(qr_data)
        self.generatedPass.emit(passB64)
        print("pass")

    def sendPass(self):
        self.status.emit("Sending Pass via email...")
        retVal = sendMail(self.rno, self.passType)
        self.result.emit(str(retVal))
        self.finished.emit()

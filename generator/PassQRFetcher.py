from PyQt5 import QtCore
from PassUtil import *
from time import sleep

class PassFetcher(QtCore.QObject):
    status = QtCore.pyqtSignal(str)
    generatedPass = QtCore.pyqtSignal(bytes)
    mailRes = QtCore.pyqtSignal(int)
    error = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()
    def __init__(self, rno, passType):
        super().__init__(None)
        self.rno, self.passType = rno, "daily" if passType==1 else "single-use"
        if self.passType == None:
            self.error.emit("Invalid Pass Type")

    def run(self):
        res = self.fetchPass()
        if res: self.sendPass()
        self.finished.emit()

    def fetchPass(self):
        self.status.emit("Fetch QR code...")
        qr_data = fetchQR(self.rno, self.passType)

        print(qr_data)
        if qr_data.get("success") == False:
            self.error.emit(qr_data.get("msg"))
            return False

        self.status.emit("Generating Pass...")
        passB64 = genPass(qr_data)
        self.generatedPass.emit(passB64)
        return True

    def sendPass(self):
        self.status.emit("Sending Pass via email...")
        mailStatus = sendMail(self.rno)
        self.mailRes.emit(mailStatus)
        self.finished.emit()

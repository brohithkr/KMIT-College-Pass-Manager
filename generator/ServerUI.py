from PyQt5 import QtCore, QtWidgets, QtGui
from sys import exit
from typing import Any
import requests

SERVERURL = ""

class ServerThreadHandler(QtCore.QObject):
    crash = QtCore.pyqtSignal(int)
    error = QtCore.pyqtSignal(str)
    success = QtCore.pyqtSignal()
    def __init__(self, parent: QtCore.QObject | None = None):
        super().__init__(parent)
    
    def login(self, UID, PWD):
        response = None

        try:
            response = requests.get(f"{SERVERURL}/api/login/mentors", json={"uid": UID, "password": PWD}).status_code
        except (requests.ConnectionError, requests.Timeout):
            self.error.emit("Internet Error! Try Again.")
            return

        if response == 200:
            self.success.emit()
        elif response == 401: 
            self.error.emit("Invalid credentials.")
        else:
            self.crash.emit(response)
            print("Unexpected server-side error occured.")
            print("Response:", response)
        
class ServerDialog(QtWidgets.QDialog):
    invalid = QtCore.pyqtSignal()
    def __init__(self, parent=None, creds=None, handler:ServerThreadHandler = None, verify = False):
        super().__init__(parent=parent)
        self.setWindowTitle("Server Login" if verify else "Verify User")

        self.handler = handler
        self.verify = verify

        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)

        if not verify:
            self.userid = QtWidgets.QLineEdit(self)
            self.userid.setPlaceholderText("User ID")
        else:
            self.userid = QtWidgets.QLabel(self)

        self.password = QtWidgets.QLineEdit(self)
        self.password.setPlaceholderText("p455w0rd")
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, self)

        layout = QtWidgets.QFormLayout(self)
        layout.addRow("User ID", self.userid)
        layout.addRow("Password", self.password)
        layout.addWidget(buttonBox)

        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        
        if creds:
            self.userid.setText(creds["uid"])
            self.password.setText(creds["pwd"])

        def okaction(verify = False):
            UID = self.userid.text()
            if UID == '' or (self.password.text() == '' and not verify):
                QtWidgets.QMessageBox.critical(self.parent(), "Error!", "Empty Data.")
            elif self.password.text() == '' and verify:
                return
            else:
                self.accept()

        if creds: okaction(self.verify)
        buttonBox.accepted.connect(okaction)

    def getInputs(self):
        return (self.userid.text(), self.password.text())
    
    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        if not self.verify: exit()
        else: self.invalid.emit()
    
    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() != QtCore.Qt.Key.Key_Escape:
            QtWidgets.QDialog.keyPressEvent(self, e)

    def error(self, msg):
        QtWidgets.QMessageBox.critical(self.parent(), "Error!", msg)
        self.userid.setFocus()
        self.show()
        self.handler.error.disconnect(self.error)
        self.handler.error.connect(self.error)

    def success(self):
        QtWidgets.QMessageBox.information(self.parent(), "Success", 
            "Server Login successful." if not self.verify else \
            "Validating extra Pass.")

    def crash(self, response):
        QtWidgets.QMessageBox.critical(self.parent(), "Server Error!!", f"Unexpected server-side error occured when trying to Log in.\nResponse code: {response}")
        exit()


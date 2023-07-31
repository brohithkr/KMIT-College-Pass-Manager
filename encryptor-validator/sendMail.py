import smtplib, ssl, sys
# from PyQt5 import QtCore
from base64 import b64decode as b64d
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText 
from email.mime.image import MIMEImage
from os.path import dirname, abspath
# from genImage import *
from configparser import ConfigParser

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

host, port, mail, pwd = None, None, None, None
#Get host, port, mail, pwd
cfg = ConfigParser()
cfg.read(f"{BASE_DIR}/data/.config.ini")
SERVERURL, KEY = cfg["Server"]["serverurl"], cfg["Server"]["key"]
mail, host, port, pwd = cfg["Mail"]["mail"], cfg["Mail"]["host"], cfg["Mail"]["port"], cfg["Mail"]["pwd"]

class Mailer(QtCore.QObject):
    status = QtCore.pyqtSignal(str)
    QR = QtCore.pyqtSignal(str)
    Pass = QtCore.pyqtSignal(bytes)
    finished = QtCore.pyqtSignal()
    result = QtCore.pyqtSignal(str)
    timeoutError = QtCore.pyqtSignal()
    def __init__(self, name, rno, email,):
        super().__init__(None)
        self.name, self.rno, self.email = name, rno, email
    def run(self):
        self.status.emit("Generating QR code...")
        qrB64 = genQR(self.name, self.rno)
        self.QR.emit(qrB64)

        self.status.emit("Generating Pass...")
        passB64 = genPass(qrB64)
        self.Pass.emit(passB64)

        self.status.emit("Sending Pass via email...")
        retVal = sendMail(self.name, self.email, passB64)
        self.result.emit(str(retVal))
        self.finished.emit()

def sendMail(name: str, receiver_mail: str, passB64: bytes) -> bool | None:
    with smtplib.SMTP_SSL(host, port, ssl.create_default_context()) as server:
        html = f'''
        <html>
            <body>
                <span style="color: green">< This is a computer generated email. ></span>
                <h1>Hi {name}! Here's your awaited Pass.</h1>
                <p>Hurray! You just got your Invite pass for KMIT fest 2023.</p>
                <p>Reserve this date in your calender.</p>
                <h3>Don't share this to anyone. This pass is valid only once.</h3>
                <img src="cid:Pass.png" alt="Pass Preview"/>
            </body>
        </html>
        '''

        img = MIMEImage(b64d(passB64))
        img.add_header('Content-ID', "<Pass.png>")
        img.add_header('X-Attachment-Id', "Pass.png")
        img['Content-Disposition'] = 'inline; filename=Pass.png'

        msg = MIMEMultipart()
        msg['From'] = mail
        msg['To'] = receiver_mail
        msg['Subject'] = 'Your awaited Invitation to KMIT fest.'
        msg.attach(MIMEText(html, "html"))
        msg.attach(img)
        server.login(mail, pwd)
        try:
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        except smtplib.SMTPRecipientsRefused:
            return False
        except Exception as e:
            print(type(e), e)
            return None
    return True
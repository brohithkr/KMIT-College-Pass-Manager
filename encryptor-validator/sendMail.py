import smtplib, ssl, sys
from base64 import b64decode as b64d
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText 
from email.mime.image import MIMEImage
from os.path import dirname, abspath, isfile
from configparser import ConfigParser
import dbconnector as db


# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

host, port, mail, pwd = None, None, None, None
#Get host, port, mail, pwd

if isfile(f"{BASE_DIR}/.config.ini"):
    cfg = ConfigParser()
    cfg.read(f"{BASE_DIR}/.config.ini")
    mail, host, port, pwd = cfg["mail"]["mail"], cfg["mail"]["host"], cfg["mail"]["port"], cfg["mail"]["pwd"]
else:
    host, port, mail, pwd = os.environ.get("MAILHOST"), os.environ.get("MAILPORT"), os.environ.get("MAIL"), os.environ.get("MAILPWD")


def sendMail(name: str, receiver_mail: str, passB64: str, passType: str ) -> bool | None:
    with smtplib.SMTP_SSL(host, port, ssl.create_default_context()) as server:
        html = f'''
        <html>
            <body>
                <span style="color: green">< This is a computer generated email. ></span>
                <h1>Hi {name}! Here's your {passType} Pass.</h1>
                <h3>Don't share this to anyone.</h3>
                <img src="cid:Pass.png" alt="Pass Preview"/>
            </body>
        </html>
        '''

        img = MIMEImage(b64d(passB64.encode()))
        img.add_header('Content-ID', "<Pass.png>")
        img.add_header('X-Attachment-Id', "Pass.png")
        img['Content-Disposition'] = 'inline; filename=Pass.png'

        msg = MIMEMultipart()
        msg['From'] = mail
        msg['To'] = receiver_mail
        msg['Subject'] = f'Your {passType} Pass'
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
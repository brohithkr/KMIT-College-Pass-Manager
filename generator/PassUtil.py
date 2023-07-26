from io import BytesIO
from base64 import b64decode as b64d, b64encode as b64e
from PIL import Image
from os.path import dirname, abspath
from configparser import ConfigParser
import sys, requests
from ServerUI import SERVERURL

BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

cfg = ConfigParser()
cfg.read(f"{BASE_DIR}/data/.config.ini")
UID, PWD = cfg["Login"]["uid"], cfg["Login"]["pwd"]

def fetchQR(rno, passtype) -> str:           
    qrB64 = requests.post(f"{SERVERURL}/PassQR",
        json={
            "uid": UID,
            "pwd": PWD,
            "rno": rno,
            "type": passtype
        }).json()["b64qr"]
    return qrB64

def genPass(qrB64: str, passType) -> bytes:
    qr = Image.open(BytesIO(b64d(qrB64))).resize((200, 200))
    template = Image.open(f"{BASE_DIR}/data/Template.png")
    img = template.copy()
    img.paste(qr, (50, 450))
    buffer = BytesIO()
    img.save(buffer, format='png')
    passB64 = b64e(buffer.getvalue())
    return passB64

def sendMail(rno, passType) -> bool | None:
    return requests.post(f"{SERVERURL}/sendMail", json={"rno": rno, "type": passType}).json()["status"]
from io import BytesIO
from base64 import b64decode as b64d, b64encode as b64e
from PIL import Image, ImageDraw, ImageFont
from os.path import dirname, abspath, join as joinpath
from configparser import ConfigParser
from datetime import date
import sys, requests
from ServerUI import SERVERURL

BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

DATA_DIR = joinpath(dirname(abspath(__file__)), "data")

cfg = ConfigParser()
cfg.read(f"{BASE_DIR}/data/.config.ini")
UID, PWD = cfg["Login"]["uid"], cfg["Login"]["pwd"]

def fetchQR(rno, passtype) -> str:           
    passqr_data = requests.post(f"{SERVERURL}/PassQR",
        json={
            "uid": UID,
            "pwd": PWD,
            "rno": rno,
            "type": passtype
        })
    return passqr_data

# from https://itnext.io/how-to-wrap-text-on-image-using-python-8f569860f89e + modifications
def text_wrap(text, font, max_width):
        lines = []
        if font.getbbox(text)[2] <= max_width: lines.append(text)
        else:
            words = text.split(' ')
            i = 0
            while i < len(words):
                line = ''
                while i < len(words) and font.getbbox(line + words[i])[2] <= max_width:
                    line = line + words[i]+ " "
                    i += 1
                if not line:
                    line = words[i]
                    i += 1
                lines.append(line)
        return lines

def genPass(pass_data: dict, passType: str) -> bytes:
    qr = Image.open(BytesIO(b64d(pass_data["b64qr"]))).resize((312, 312))
    studentimg = requests.get(f"http://teleuniv.in/sanjaya/student-images/{pass_data['rno']}.jpg").content
    studentimg = Image.open(BytesIO(studentimg)).resize((188, 252))
    template = Image.open(f"{BASE_DIR}/data/{passType}.png")

    textfont = ImageFont.truetype(f"{DATA_DIR}/Lora.ttf", 24)
    today = date.today()
    today = today.strftime(r"%d/%m/%Y")
    details = text_wrap(pass_data["name"], textfont, 300)
    details.extend(text_wrap(f"{pass_data['rno']} {pass_data['class']}", textfont, 300))

    img = template.copy()
    img.paste(qr, (76, 154))
    img.paste(studentimg, (496, 154))

    datefont = ImageFont.truetype(f"{DATA_DIR}/Verdana.ttf", 40)
    painter = ImageDraw.Draw(img)
    painter.text((110, 470), today, fill=(0,0,0), font=datefont)
    y, height = 415, textfont.getbbox("hg")[3]+5
    for line in details:
        painter.text((470, y), line, fill=(2,2,2), font=textfont)
        y += height

    buffer = BytesIO()
    img.save(buffer, format='png')
    passB64 = b64e(buffer.getvalue())
    img.show()
    return passB64

def sendMail(rno, passType) -> bool | None:
    return requests.post(f"{SERVERURL}/sendMail", json={"rno": rno, "type": passType}).json()["status"]
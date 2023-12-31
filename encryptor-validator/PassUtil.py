from io import BytesIO
from base64 import b64decode as b64d, b64encode as b64e
from PIL import Image, ImageDraw, ImageFont
import os
from os.path import dirname, abspath
from configparser import ConfigParser
from datetime import date
import sys, requests

BASE_DIR = None
if getattr(sys, 'frozen', False):
    BASE_DIR = dirname(sys.executable)
elif __file__:
    BASE_DIR = dirname(abspath(__file__))

SERVERURL, HKEY = None, None

if os.path.isfile(f"{BASE_DIR}/.config.ini"):
    cfg = ConfigParser()
    cfg.read(f"{BASE_DIR}/.config.ini")
    SERVERURL, HKEY = cfg.get("server","SERVERURL"), cfg.get("server","HKEY")
else:
    SERVERURL, HKEY = os.environ.get("SERVERURL"), os.environ.get("HKEY")
    print(SERVERURL, HKEY)
    if None in (SERVERURL, HKEY) :
        raise Exception("Please provide environment variables or .config.ini")

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

def genPass(pass_data: dict, passType: str) -> str:
    qr = Image.open(BytesIO(b64d(pass_data["b64qr"].encode()))).resize((312, 312))
    studentimg = requests.get(f"http://teleuniv.in/sanjaya/student-images/{pass_data['rno']}.jpg").content
    studentimg = Image.open(BytesIO(studentimg)).resize((188, 252))
    template = Image.open(f"{BASE_DIR}/data/{passType}.png")

    textfont = ImageFont.truetype(f"{BASE_DIR}/data/Lora.ttf", 24)
    today = date.today()
    today = today.strftime(r"%d/%m/%Y")
    details = text_wrap(pass_data["name"], textfont, 300)
    details.extend(text_wrap(f"{pass_data['rno']} {pass_data['section']}", textfont, 300))

    img = template.copy()
    img.paste(qr, (76, 154))
    img.paste(studentimg, (496, 154))

    datefont = ImageFont.truetype(f"{BASE_DIR}/data/Verdana.ttf", 40)
    painter = ImageDraw.Draw(img)
    painter.text((110, 470), today, fill=(0,0,0), font=datefont)
    y, height = 415, textfont.getbbox("hg")[3]+5
    for line in details:
        painter.text((470, y), line, fill=(2,2,2), font=textfont)
        y += height

    buffer = BytesIO()
    img.save(buffer, format='png')
    passB64 = b64e(buffer.getvalue())
    return passB64.decode()
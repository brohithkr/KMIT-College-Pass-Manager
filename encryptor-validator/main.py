from fastapi import FastAPI, Request, Header
from pydantic import BaseModel
from typing import Annotated, Union
import pyqrcode
from PassUtil import genPass
import dbconnector as db
from crypto import hashhex, signData, unsignData
import os
from configparser import ConfigParser

# config params

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVERURL, HKEY = None, None

if os.path.isfile(f"{BASE_DIR}/.config.ini"):
    configur = ConfigParser()
    configur.read(f"{BASE_DIR}/.config.ini")
    SERVERURL, HKEY = configur.get("server","SERVERURL"), configur.get("server","HKEY")
else:
    SERVERURL, HKEY = os.environ.get("SERVERURL"), os.environ.get("HKEY")
    print(SERVERURL, HKEY)
    if None in (SERVERURL, HKEY) :
        raise Exception("Please provide environment variables or .config.ini")


# Models

class User(BaseModel):
    uid: str
    name: Union[str, None] = None
    password: str
    section: Union[str, None] = None


class StatusResponse(BaseModel):
    success: Union[bool, None]
    msg: Union[str, None] = None
    # reason: str | None = None

class reqPass(BaseModel):
    uid: str
    pwd: str
    rno: str
    passType: str

class Pass(BaseModel):
    rno: str
    name: str
    section: str
    b64qr: str
    passType: str




# functions


app = FastAPI()


@app.post("/api/register/{usertype}")
async def add_user(usertype,key: Annotated[str, Header()], user: User) -> StatusResponse:
    validtypes = ["mentors", "verifiers"]
    if usertype not in validtypes:
        return StatusResponse(success=False, msg= "Invalid type access")
    if usertype=="verifiers" and user.section!= None:
        return StatusResponse(success=False, msg= "Invalid parameters")
    if hashhex(key) != HKEY:
        return StatusResponse(success=False, msg= "Unauthorized Access")
    conn = db.connect()
    if db.get_data(conn, usertype, user.uid):
        return StatusResponse(success=False, msg= f"{usertype[:-1]} already exists")
    if usertype=="mentors":
        db.add_mentor(conn, user.dict())
    elif usertype=="verifiers":
        verifierDict = user.dict()
        verifierDict.pop("section",None)
        db.add_verifiers(conn,verifierDict)
    return StatusResponse(success=True, msg = f"{usertype[:-1]} {user.uid} has been registered succesfully")


@app.get("/api/login/{usertype}")
async def is_valid_user(usertype: str, user: User) -> StatusResponse:
    validtypes = ["mentors", "verifiers"]
    if usertype not in validtypes:
        return StatusResponse(success=False, msg= "Invalid type access")
    conn = db.connect()
    userdata = db.get_data(conn, usertype, user.uid)

    if not userdata:
        return StatusResponse(success=False, msg= "invalid uid")

    if userdata["password"] != hashhex(user.password):
        return StatusResponse(success=False, msg= "invalid password")
    return StatusResponse(success=True, msg = f"Valid {usertype[:-1]}, Login successful")

@app.post("/api/issuepass")
def issuepass(reqpass: reqPass, fullimage: bool = False) -> Pass:
    conn = db.connect()
    mentor_data = db.get_data(conn, "mentors", reqpass.uid)
    student_data = db.get_data(conn, "students", reqpass.rno)

    if not mentor_data:
        return StatusResponse(success=False, msg= "invalid uid")

    if mentor_data["password"] != hashhex(reqpass.pwd):
        return StatusResponse(success=False, msg= "invalid password")
    
    if mentor_data["section"] != student_data["section"]:
        return StatusResponse(success=False, msg= "Unautherized Pass Issue")
    
    pass_data = db.get_data(conn, "passes", reqpass.rno)

    if pass_data:
        if not fullimage:
            return Pass(rno=reqpass.rno,**pass_data)
        else:
            pass_data['rno'] = reqpass.rno
            pass_data["b64qr"] = genPass(pass_data, reqpass.passType).decode()
            return Pass(**pass_data)

    signedrno = signData(reqpass.rno,mentor_data["private_key"],reqpass.uid)
    signed_data = f"{signedrno}@{reqpass.uid}"
    qr = pyqrcode.create(signed_data)
    b64qr = qr.png_as_base64_str()

    resPass = Pass(rno=reqpass.rno, name=student_data["name"], section=student_data["section"], b64qr=b64qr, passType=reqpass.passType)

    db.set_data(conn,"passes","rno",resPass.dict())

    if fullimage:
        resPass.b64qr = genPass(student_data, reqPass.passType).decode()

    return resPass





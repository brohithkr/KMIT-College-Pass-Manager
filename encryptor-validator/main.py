from fastapi import FastAPI, Request, Header
from pydantic import BaseModel
from typing import Annotated, Union
import dbconnector as db
from crypto import hashhex
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
    rno: str
    name: str
    section: str
    passType: str
    validTill: str

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
    # print(userdata,hashhex(user.password))
    if userdata["password"] != hashhex(user.password):
        return StatusResponse(success=False, msg= "invalid password")
    return StatusResponse(success=True, msg = f"Valid {usertype[:-1]}, Login successful")

@app.post("/api/issuepass")
def issuepass(passType: str, reqpass: reqPass) -> Pass:
    pass
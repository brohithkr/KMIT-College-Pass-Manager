from fastapi import FastAPI, Request, Header
from pydantic import BaseModel
from typing import Annotated
import dbconnector as db
from crypto import hashhex
import os

# config params

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVERURL, HKEY = None, None
with open(f"{BASE_DIR}/.configserver") as f:
    for line in f.readlines():
        exec(line)

# Models


class User(BaseModel):
    uid: str
    name: str | None = None
    password: str
    section: str | None = None


class StatusResponse(BaseModel):
    success: bool | None
    msg: str | None = None
    # reason: str | None = None


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
    conn = db.connect("user_data.db")
    if db.get_data(conn, usertype, user.uid):
        return StatusResponse(success=False, msg= f"{usertype[:-1]} already exists")
    if usertype=="mentors":
        db.add_mentor(conn, user.dict())
    elif usertype=="verifiers":
        db.add_verifiers(conn,user.dict())
    return StatusResponse(success=True, msg = f"{usertype[:-1]} {user.uid} has been registered succesfully")


@app.get("/api/login/{usertype}")
async def is_valid_user(usertype: str, user: User) -> StatusResponse:
    validtypes = ["mentors", "verifiers"]
    if usertype not in validtypes:
        return StatusResponse(success=False, msg= "Invalid type access")
    conn = db.connect("user_data.db")
    userdata = db.get_data(conn, usertype, user.uid, keys=["uid", "password"])
    if not userdata:
        return StatusResponse(success=False, msg= "invalid uid")
    # print(userdata,hashhex(user.password))
    if userdata[1] != hashhex(user.password):
        return StatusResponse(success=False, msg= "invalid password")
    return StatusResponse(success=True, msg = f"Valid {usertype[:-1]}, Login successful")




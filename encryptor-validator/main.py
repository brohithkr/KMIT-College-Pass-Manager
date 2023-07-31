from fastapi import FastAPI, Request, Header, Response, status
from pydantic import BaseModel
from typing import Annotated, Union, List
import pyqrcode
from PassUtil import genPass
import dbconnector as db
from crypto import hashhex, signData, unsignData
from configparser import ConfigParser
import os
from datetime import datetime,date,timedelta
from pytz import timezone

# config params

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVERURL, HKEY = None, None

if os.path.isfile(f"{BASE_DIR}/.config.ini"):
    configur = ConfigParser()
    configur.read(f"{BASE_DIR}/.config.ini")
    SERVERURL, HKEY = configur.get("server", "SERVERURL"), configur.get(
        "server", "HKEY"
    )
else:
    SERVERURL, HKEY = os.environ.get("SERVERURL"), os.environ.get("HKEY")
    print(SERVERURL, HKEY)
    if None in (SERVERURL, HKEY):
        raise Exception("Please provide environment variables or .config.ini")

DAILY_PASS_VALIDITY = timedelta(int(365/2))

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
    issueDate: str


class reqVer(BaseModel):
    uid: str
    pwd: str
    data: str


# functions

# def is_valid_user(user_type,user: User):
#     validtypes = ["mentors", "verifiers"]
#     if user_type not in validtypes:
#         return StatusResponse(success=False, msg="Invalid type access")
#     conn = db.connect()
#     userdata = db.get_data(conn, user_type, user.uid)

#     if not userdata :
#         return StatusResponse(success=False, msg="invalid uid")

#     if userdata["password"] != hashhex(user.password):
#         return StatusResponse(success=False, msg="invalid password")
#     return StatusResponse(success=True, msg=f"Valid {user_type[:-1]}, Login successful")


app = FastAPI()


@app.post("/api/register/{usertype}")
async def add_user(
    usertype, key: Annotated[str, Header()], user: User
) -> StatusResponse:
    validtypes = ["mentors", "verifiers"]
    if usertype not in validtypes:
        return StatusResponse(success=False, msg="Invalid type access")
    if usertype == "verifiers" and user.section != None:
        return StatusResponse(success=False, msg="Invalid parameters")
    if hashhex(key) != HKEY:
        return StatusResponse(success=False, msg="Unauthorized Access")
    conn = db.connect()
    if db.get_data(conn, usertype, user.uid):
        return StatusResponse(success=False, msg=f"{usertype[:-1]} already exists")
    if usertype == "mentors":
        db.add_mentor(conn, user.dict())
    elif usertype == "verifiers":
        verifierDict = user.dict()
        verifierDict.pop("section", None)
        db.add_verifiers(conn, verifierDict)
    return StatusResponse(
        success=True, msg=f"{usertype[:-1]} {user.uid} has been registered succesfully"
    )


@app.get("/api/login/{usertype}")
async def is_valid_user(usertype: str, user: User, resp: Response) -> Union[StatusResponse, Pass]:
    validtypes = ["mentors", "verifiers"]
    if usertype not in validtypes:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="Invalid type access")
    conn = db.connect()
    userdata = db.get_data(conn, usertype, user.uid)
    if not userdata:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="invalid uid")
    # if userdata["uid"] != user.uid:
    #     return StatusResponse(success=False, msg="invalid uid")
    if userdata["password"] != hashhex(user.password):
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="invalid password")
    return StatusResponse(success=True, msg=f"Valid {usertype[:-1]}, Login successful")


@app.post("/api/issuepass")
async def issuepass(reqpass: reqPass, resp: Response, fullimage: bool = False) -> Union[Pass, StatusResponse]:
    conn = db.connect()
    mentor_data = db.get_data(conn, "mentors", reqpass.uid)
    student_data = db.get_data(conn, "students", reqpass.rno)

    if not mentor_data:
        return StatusResponse(success=False, msg="invalid uid")

    if mentor_data["password"] != hashhex(reqpass.pwd):
        return StatusResponse(success=False, msg="invalid password")

    if mentor_data["section"] != student_data["section"]:
        return StatusResponse(success=False, msg="Unautherized Pass Issue")

    pass_data = db.get_data(conn, "passes", reqpass.rno)

    # alreadyOwns = False
    resp.headers["alreadyOwns"] = "false"

    if pass_data:
        if reqpass.passType != pass_data["passType"]:
            print(pass_data["passType"], reqpass.passType)
            return StatusResponse(
                success=False,
                msg=f"{student_data['name']} already owns a {pass_data['passType']} pass.",
            )
        # alreadyOwns = True
        resp.headers["alreadyOwns"] = "true"
        if not fullimage:
            return Pass(rno=reqpass.rno, **pass_data)
        else:
            pass_data["rno"] = reqpass.rno
            pass_data["b64qr"] = genPass(pass_data, reqpass.passType).decode()
            
            return Pass(rno=reqpass.rno, **pass_data)

    signedrno = signData(reqpass.rno, mentor_data["private_key"], reqpass.uid)
    signed_data = f"{signedrno}@{reqpass.uid}"
    qr = pyqrcode.create(signed_data)
    b64qr = qr.png_as_base64_str()

    resPass = Pass(
        rno=reqpass.rno,
        name=student_data["name"],
        section=student_data["section"],
        b64qr=b64qr,
        passType=reqpass.passType,
        issueDate=datetime.now(timezone("Asia/Kolkata")).strftime("%d-%m-%Y"),
    )

    db.set_data(conn, "passes", "rno", resPass.dict())

    if fullimage:
        resPass.b64qr = genPass(student_data, reqPass.passType).decode()

    return resPass.dict().update("alreadyOwns",alreadyOwns)

# @app.get("/api/get_issued_passes")
# def 

@app.post("/api/get_scan_history")
def get_scan_history(req: reqVer):
    pass




# @app.post("/api/get_history")
# def get_history(reqVer: reqVerification) -> Union[List,StatusResponse]:
#     verifier_data = db.get_data(conn, "verifiers", reqVer.uid)
#     if not verifier_data:
#         return StatusResponse(success=False, msg="Invalid verifier UID")
#     elif verifier_data["password"] != hashhex(reqVer.pwd):
#         return StatusResponse(success=False, msg="Invalid verifier password")
#     sign, uid = signed_data.split("@")
#     conn = db.connect()
#     mentor_key = db.get_data(conn, "mentors", uid)["public_key"]
#     rno = None
#     try:
#         rno = unsignData(sign, mentor_key)
#     except:
#         return StatusResponse(success=False, msg="Invalid Signature")

#     pass_details = db.get_data(conn, "passes", rno)
#     history = db.get_data(conn, "scan_history", rno)

#     history_today = None

#     if not pass_details:
#         return StatusResponse(success=False, msg="Not Active Pass")

#     if pass_details["passType"] == "daily":
#         pass_issue_date = datetime.strptime(
#             pass_details["issueDate"], "%d-%m-%Y"
#         ).date()
#         if date.today() - datetime.strptime(
#             pass_details["issueDate"], "%d-%m-%Y"
#         ).date() > timedelta(days=1):
#             return StatusResponse(success=False, msg="Pass Expired")
#         history_today = []
#         for i in history[-2:]:
#             idate = datetime.strptime(i, "%d-%m-%Y %H:%M:%S")
#             today = datetime.now(timezone("Asia/Kolkata"))
#             if (today - idate).days == 0:
#                 history_today.append(i)
#         # if len(history_today) >= 2:
#         #     return history_today
#     if pass_details["passType"] == "single-use":
#         if len(history) >= 2:
#             set_data(conn, "expired_passes", rno, pass_details)
#             return history

#     # if 

#     db.set_data(
#         conn,
#         "scan_history",
#         rno,
#         [datetime.now(timezone("Asia/Kolkata")).strftime("%d-%m-%Y %H:%M:%S")],
#     )


#     return history

    # if not student_data:
    #     return StatusResponse(success=False, msg="Insuffitient data")
    # mentor_data = db.get_data(conn, "mentors", uid)

    # if not unsignData(rno, signed_data, mentor_data["public_key"]):
    #     return StatusResponse(success=False, msg="Invalid Pass")
    # return StatusResponse(success=True, msg="Pass Verified")






@app.head("/wake_up")
def wake_up():
    return Response()

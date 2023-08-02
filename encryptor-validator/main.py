from fastapi import FastAPI, Request, Header, Request, Response, status
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Annotated, Union, List
import pyqrcode
from PassUtil import genPass
import dbconnector as db
from sendMail import sendMail
from crypto import hashhex, signData, unsignData
from qrscanner import scanQR
from configparser import ConfigParser
import os
import json
from datetime import datetime, date, timedelta
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

DAILY_PASS_VALIDITY = timedelta(int(365 / 2))

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


class History(BaseModel):
    history: List

class UnSignedData(BaseModel):
    isValidSign: bool
    rno: Union[str, None]
    failure_reason: Union[str, None] = None

class reqMail(BaseModel):
    uid: str
    pwd: str
    rno: str


# functions


def is_val_user(conn, user_type, user: User):
    validtypes = ["mentors", "verifiers"]
    if user_type not in validtypes:
        return "invalid type access", False
    userdata = db.get_data(conn, user_type, user.uid)
    if not userdata:
        return "invalid uid", False
    if userdata["password"] != hashhex(user.password):
        return "invalid password", False
    return "valid user", True


def filter_todays_history(hist):
    todays_hist = []
    # print(hist[-2:],hist)
    for i in hist[-2:]:
        li = json.loads(i)
        datestr = li[0]
        print(datestr)
        if (datetime.now() - datetime.strptime(datestr,"%d-%m-%Y %H:%M:%S")).days == 0:
            todays_hist.append(li)
    return todays_hist


app = FastAPI()

app.mount("/static", StaticFiles(directory="templates/static"), name="static")

templates = Jinja2Templates(directory="templates")


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


@app.get("/api/login/{usertype}", status_code=200)
async def is_valid_user(
    usertype: str, user: User, resp: Response
) -> Union[StatusResponse, Pass]:
    validtypes = ["mentors", "verifiers"]
    if usertype not in validtypes:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="Invalid type access")
    conn = db.connect()
    res = is_val_user(conn, usertype, user)[0]
    if res == "invalid uid":
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="invalid uid")
    if res == "invalid password":
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="invalid password")
    return StatusResponse(success=True, msg=f"Valid {usertype[:-1]}, Login successful")


@app.post("/api/issuepass")
async def issuepass(
    reqpass: reqPass, resp: Response, fullimage: bool = False
) -> Union[Pass, StatusResponse]:
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
        resPass.b64qr = genPass(resPass.dict(), reqpass.passType).decode()

    return resPass.dict().update("alreadyOwns", alreadyOwns)


@app.post("/sendMail")
async def send_mail(req: reqMail, resp: Response) -> StatusResponse:
    conn = db.connect()
    if not is_val_user(conn, "mentors", User(uid=req.uid, password=req.pwd))[1]:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="Unauthorized Access")
    student_data = db.get_data(conn, "students", req.rno)
    pass_details = db.get_data(conn, "passes", req.rno)

    pass_details["rno"] = req.rno
    b64img = genPass(pass_details, pass_details["passType"])

    res = sendMail(
        student_data["name"], student_data["email"], b64img, pass_details["passType"]
    )
    if not res:
        resp.status_code = status.HTTP_409_CONFLICT
    return StatusResponse(success=True, msg="email sent")

@app.post("/api/verify_sign")
def verify_sign(req: reqVer, resp: Response) -> Union[UnSignedData, StatusResponse]:
    conn = db.connect()
    if not is_val_user(conn, "verifiers", User(uid=req.uid, password=req.pwd))[1]:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="Unauthorized Access")

    signed_data = scanQR(req.data)
    # print(signed_data)
    if signed_data == None:
        return UnSignedData(isValidSign=False, rno=None, failure_reason="No QR Code Found")
    if '@' not in signed_data:
        return UnSignedData(isValidSign=False, rno=None, failure_reason="This QR Code is not a Pass")
    
    enrno, uid = signed_data.split('@')

    pubkey = db.get_data(conn, "mentors", uid)['public_key']

    unsignedData = UnSignedData(rno=None, isValidSign=False)
    # print(enrno, pubkey) 
    try:
        unsignedData.rno = unsignData(enrno, pubkey)
        unsignedData.isValidSign = True
    except Exception as e:
        print("error",e)
        unsignedData = UnSignedData(rno=None, isValidSign=False, failure_reason="Invalid Signature")
    
    return unsignedData


@app.get("/api/get_scan_history")
def get_scan_history(req: reqMail, resp: Response) -> Union[History, StatusResponse]:
    conn = db.connect()
    is_val = (
        is_val_user(conn, "mentor", User(uid=req.uid, password=req.pwd))[1]
        or is_val_user(conn, "verifiers", User(uid=req.uid, password=req.pwd))[1]
    )
    if not is_val:
        return StatusResponse(success=False, msg="Invalid Credentials")
    history = db.get_data(conn, "scan_history", req.rno)
    today_history = filter_todays_history(history)
    return History(history=today_history)


@app.post("/api/audit_scan", status_code=200)
def audit_scan(req: reqMail, resp: Response) -> StatusResponse:
    conn = db.connect()
    is_val = (
        is_val_user(conn, "verifiers", User(uid=req.uid, password=req.pwd))[1]
    )
    if not is_val:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="Invalid Credentials")
    history = db.get_data(conn, "scan_history", req.rno)
    todays_history = filter_todays_history(history)
    if len(todays_history) >= 2:
        resp.status_code = status.HTTP_400_BAD_REQUEST
        pass_data = db.get_data(conn, "passes", req.rno)
        if pass_data["passType"] == "single-use":       
            db.set_data(conn, "expired_passes", req.rno, [pass_data["issueDate"]])
            db.delete_data(conn, "scan_history", req.rno)
        return StatusResponse(success=False, msg="Already Scanned twice")
    db.set_data(
        conn,
        "scan_history",
        req.rno,
        [json.dumps([datetime.now(timezone("Asia/Kolkata")).strftime("%d-%m-%Y %H:%M:%S"), req.uid])],
    )
    return StatusResponse(success=True, msg="Pass Scan Audited")
@app.get("/scan")
def scan(req: Request):
    return templates.TemplateResponse("QRscanner.html", {"request": req})


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

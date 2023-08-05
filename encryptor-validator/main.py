from fastapi import FastAPI, Request, Header, Request, Response, status, Cookie
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
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
        print(
            (datetime.now().day - datetime.strptime(datestr, "%d-%m-%Y %H:%M:%S").day),
            "check",
        )
        if (
            datetime.now().day - datetime.strptime(datestr, "%d-%m-%Y %H:%M:%S").day
        ) == 0:
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


@app.post("/api/login/{usertype}", status_code=200)
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
        print(pass_data["passType"], reqpass.passType)
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
    
    resp.headers["alreadyOwns"] = "false"
    return resPass.dict()


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

    if student_data["email"] == "":
        resp.status_code = status.HTTP_400_BAD_REQUEST
        return StatusResponse(success=False, msg="Student email not available.")

    res = sendMail(
        student_data["name"], student_data["email"], b64img, pass_details["passType"]
    )
    if not res:
        resp.status_code = status.HTTP_409_CONFLICT
        return StatusResponse(success=False, msg="Unexpected Error")
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
        # resp.status_code = status.HTTP_204_NO_CONTENT
        return UnSignedData(
            isValidSign=False, rno=None, failure_reason="No QR Code Found"
        )
    if "@" not in signed_data:
        return UnSignedData(
            isValidSign=False, rno=None, failure_reason="This QR Code is not a Pass"
        )

    enrno, uid = signed_data.split("@")

    pubkey = db.get_data(conn, "mentors", uid)["public_key"]

    unsignedData = UnSignedData(rno=None, isValidSign=False)
    # print(enrno, pubkey)
    try:
        unsignedData.rno = unsignData(enrno, pubkey)
        unsignedData.isValidSign = True
    except Exception as e:
        print("error", e)
        unsignedData = UnSignedData(
            rno=None, isValidSign=False, failure_reason="Invalid Signature"
        )

    return unsignedData


@app.post("/api/get_scan_history")
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
    is_val = is_val_user(conn, "verifiers", User(uid=req.uid, password=req.pwd))[1]
    if not is_val:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return StatusResponse(success=False, msg="Invalid Credentials")
    pass_data = db.get_data(conn, "passes", req.rno)
    if pass_data:
        if pass_data["passType"] == "single-use":
            if (pass_data["issueDate"]-datetime.today()).days >= 1:
                db.set_data(conn, "expired_passes", req.rno, [pass_data["issueDate"]])
                db.delete_data(conn, "passes", req.rno)
    
    pass_data = db.get_data(conn, "passes", req.rno)
    if not pass_data:
            resp.status_code = status.HTTP_400_BAD_REQUEST
            return StatusResponse(success=False, msg="Pass has Expired")
    history = db.get_data(conn, "scan_history", req.rno)
    todays_history = filter_todays_history(history)
    print(todays_history)
    if len(todays_history) >= 2:
        resp.status_code = status.HTTP_400_BAD_REQUEST
        if pass_data["passType"] == "single-use":
            db.set_data(conn, "expired_passes", req.rno, [pass_data["issueDate"]])
            db.delete_data(conn, "passes", req.rno)
        return StatusResponse(success=False, msg="Already Scanned twice")
    
    db.set_data(
        conn,
        "scan_history",
        req.rno,
        [
            json.dumps(
                [
                    datetime.now(timezone("Asia/Kolkata")).strftime(
                        "%d-%m-%Y %H:%M:%S"
                    ),
                    req.uid,
                ]
            )
        ],
    )
    return StatusResponse(success=True, msg="Pass Scan Audited")


@app.get("/login/{userType}")
def loginPage(req: Request, userType: str):
    # print(userType)
    return templates.TemplateResponse(
        "login.html", {"request": req, "userType": userType.capitalize()[:-1]}
    )

@app.get("/register/{userType}")
def register(req: Request, userType: str):
    return templates.TemplateResponse(
        "register.html", {"request": req, "userType": userType.capitalize()[:-1]}
    )

# @app.get("/register/mentors")
# def regPageMen(req: Request, resp: Response, key: str = "None"):
#     if hashhex(key) != HKEY:
#         return RedirectResponse("/display_affirm?success=False&msg=Unauthorized Access")
#     # resp.set_cookie("pwd", value=key)
#     return templates.TemplateResponse("RegMen.html", {"request": req})


# @app.get("/register/verifiers")
# def regPageVer(req: Request, key: str = "None"):
#     if hashhex(key) != HKEY:
#         return RedirectResponse("/display_affirm?success=False&msg=Unauthorized Access")
#     return templates.TemplateResponse("RegVer.html", {"request": req})

class reqval(BaseModel):
    pwd: str

@app.post("/pass_validate")
def pass_validation(req: reqval, resp: Response):
    if hashhex(req.pwd) != HKEY:
        resp.status_code = status.HTTP_401_UNAUTHORIZED
        return {"isValid": False, "message": "Invalid Password"}
    else:
        resp.status_code = status.HTTP_200_OK
        return {"isValid": True, "message": "Valid Password"}


@app.get("/scan")
def scan(req: Request):
    uid = req.cookies.get("uid")
    pwd = req.cookies.get("pwd")
    conn = db.connect()
    # print(uid, pwd)
    if not is_val_user(conn, "verifiers", User(uid=str(uid), password=str(pwd)))[1]:
        return RedirectResponse("/login/verifiers")
    

    return templates.TemplateResponse("QRscanner.html", {"request": req})


@app.get("/display_affirm")
def display_affirm(req: Request, success: bool, msg: str):
    return templates.TemplateResponse(
        "passaffirmation.html", {"request": req, "isValid": success, "message": msg}
    )


# @app.get("/")
# def home(req: Request):
#     return templates.TemplateResponse("index.html", {"request": req})


@app.get("/")
def mainPage(req: Request):
    title = "Kmit Pass Generation"
    heading = "Digital Pass Generation System"
    paths = [
        ["/adminpanel", "Admin Panel"],
        ["/login/verifiers", "Verifier Login"],
        ["/login/mentors", "Mentor Login"],
    ]
    return templates.TemplateResponse(
        "pathOptions.html",
        {"request": req, "title": title, "heading": heading, "paths": paths},
    )

@app.get("/adminpanel")
def adminPanel(req: Request):
    if hashhex(str(req.cookies.get("pwd"))) != HKEY:
        return templates.TemplateResponse("adminLogin.html", {"request": req})
    title = "Admin Panel"
    paths = [
        ["/register/mentors", "Register Mentors"],
        ["/register/verifiers", "Register Verifiers"],
    ]
    return templates.TemplateResponse(
        "pathOptions.html", {"request": req, "title": title, "heading": title, "paths": paths}
    )


@app.get("/favicon.ico")
def serve_icon():
    return FileResponse(os.path.join(app.root_path,"templates","static","QRicon2.png"), media_type="image/png")
    # return {"root":app.root_path}

@app.head("/wake_up")
def wake_up():
    return Response()

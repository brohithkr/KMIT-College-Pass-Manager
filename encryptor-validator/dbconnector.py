import sqlite3
from crypto import RSAgenerate, hashhex
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if not os.path.exists(f"{BASE_DIR}/data"):
    os.mkdir(f"{BASE_DIR}/data")
if not os.path.isfile(f"{BASE_DIR}/data/user_data.db"):
    conn = sqlite3.connect(f"{BASE_DIR}/data/user_data.db")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE mentors (
        uid             TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        password        TEXT NOT NULL,
        private_key     TEXT NOT NULL,
        public_key      TEXT NOT NULL,
        section         TEXT

    );
        """
    )
    cur.execute(
        """
        CREATE TABLE verifiers (
        uid             TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        password        TEXT NOT NULL
    );
        """
    )
    conn.commit()
    conn.close()


def connect(db_name):
    db_path = f"{BASE_DIR}/data/{db_name}"
    conn = sqlite3.connect(db_path)
    return conn


def add_mentor(conn, mentorDict):
    mentorDict["password"] = hashhex(mentorDict["password"])
    cmd = f"insert into mentors "
    mentorDict["private_key"], mentorDict["public_key"] = RSAgenerate(
        mentorDict["password"]
    )
    cmd += f"{tuple(mentorDict.keys())} values {tuple(mentorDict.values())};"
    cur = conn.cursor()
    cur.execute(cmd)
    conn.commit()


def add_verifiers(conn, verifierDict):
    verifierDict["password"] = hashhex(verifierDict["password"])
    cmd = f"insert into verifiers {tuple(verifierDict.keys())} values {tuple(verifierDict.values())};"
    cur = conn.cursor()
    cur.execute(cmd)
    conn.commit()


def get_data(conn, table_name, uid, keys=["*"]):
    cur = conn.cursor()
    keystr = str(keys).strip('[]').replace("'","")
    # print(f"select {keystr} from {table_name} where uid='{uid}'")
    res = cur.execute(
        f"select {keystr} from {table_name} where uid='{uid}'"
    ).fetchone()

    return res

    # if len(keys) == 1:
    #     return res[0]
    # else:
    #     return res


def disconnect(conn):
    conn.close()

if __name__=="__main__":
    conn = connect("user_data.db")
    get_data(conn,"mentors","johndoe",["uid","password"])
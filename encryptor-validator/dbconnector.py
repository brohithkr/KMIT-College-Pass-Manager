import sqlite3
from crypto import RSAgenerate, hashhex
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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
    cmd = f"insert into verifier {tuple(verifierDict.keys())} values f{verifierDict.values()};"
    cur = conn.cursor()
    cur.execute(cmd)
    conn.commit()


def get_data(conn, table_name, uid, keys=["*"]):
    cur = conn.cursor()
    res = cur.execute(
        f"select {str(keys).strip('[]')} from {table_name} where uid='{uid}'"
    ).fetchone()

    return res

    # if len(keys) == 1:
    #     return res[0]
    # else:
    #     return res


def disconnect(conn):
    conn.close()

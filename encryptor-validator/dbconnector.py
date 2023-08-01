import redis
# import json
import os
from crypto import RSAgenerate, hashhex
from configparser import ConfigParser

# config params

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

URL, PORT, PASSWORD = None, None, None

if os.path.isfile(f"{BASE_DIR}/.config.ini"):
    configur = ConfigParser()
    configur.read(f"{BASE_DIR}/.config.ini")
    URL, PORT, PASSWORD = (
        configur.get("database","URL"), configur.get("database","PORT"), configur.get("database","PASSWORD")
    )
else:
    URL, PORT, PASSWORD = (
        os.environ.get("DBURL"), os.environ.get("DBPORT"), os.environ.get("DBPASS")
    )
    if None in (URL, PORT, PASSWORD) :
        raise Exception("Please provide environment variables or .config.ini")


# support functions

def decode_dict(d):
    res = {}
    for key, value in d.items():
        res[key.decode()] = value.decode()
    return res

# database functions

def connect():
    conn = None
    try:
        conn = redis.Redis(
            host=URL,
            port=PORT,
            password=PASSWORD
        )
    except:
        Exception("Trouble connecting to database")
    return conn


def add_mentor(conn, mentorDict):
    mentorDict["password"] = hashhex(mentorDict["password"])
    mentorDict["private_key"], mentorDict["public_key"] = RSAgenerate(
        mentorDict["uid"]
    )
    uid = mentorDict["uid"]
    del mentorDict["uid"]
    conn.hset(f"userdata:mentors:{uid}",mapping=mentorDict)



def add_verifiers(conn, verifierDict):
    verifierDict["password"] = hashhex(verifierDict["password"])
    uid = verifierDict["uid"]
    del verifierDict["uid"]
    conn.hset(f"userdata:verifiers:{uid}",mapping=verifierDict)

def set_data(conn,table_name,primkey,data):
    if type(data) == dict:
        rno = data[primkey]
        del data[primkey]
        conn.hset(f"userdata:{table_name}:{rno}",mapping=data)
    elif type(data) == list :
        for d in data:
            conn.rpush(f"userdata:{table_name}:{primkey}",d)
       
def remove_data(conn,table_name,uid):
    conn.delete(f"userdata:{table_name}:{uid}")
        


def get_data(conn, table_name, primkey, key=None):
    res = None
    if table_name in ["scan_history","expired_passes"]:
        res = []
        for i in range(conn.llen(f"userdata:{table_name}:{primkey}")):
            res.append(conn.lindex(f"userdata:{table_name}:{primkey}",i))
        return res
    if key is None:
        res = conn.hgetall(f"userdata:{table_name}:{primkey}")
        decoded = decode_dict(res)
        return decoded
    else:
        res = conn.hget(f"userdata:{table_name}:{primkey}", key=key)
        return res


def disconnect(conn):
    conn.close()

if __name__=="__main__":
    conn = connect()
    add_mentor(conn, {
        "uid": "johndoe",
        "name": "John Doe",
        "password": "password123",
        "section": "CSE-A"
    })

    d = get_data(conn, "mentors", "johndoe", )
    print(d)

    # r = redis.Redis(
    #     host="rediss://red-cj197btph6enmk10ro6g:6S2fDrVDrNHMUJH4oHaixPNfO8yQAkLV@singapore-redis.render.com:6379",
    #     port=6379,
    #     # password="6S2fDrVDrNHMUJH4oHaixPNfO8yQAkLV"
    # )
    # # print(r.set("hello","world"))
    # print(r.get("hello"))




        

        
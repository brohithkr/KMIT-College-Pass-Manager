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
        mentorDict["password"]
    )
    uid = mentorDict["uid"]
    del mentorDict["uid"]
    conn.hset(f"userdata:mentors:{uid}",mapping=mentorDict)



def add_verifiers(conn, verifierDict):
    verifierDict["password"] = hashhex(verifierDict["password"])
    uid = verifierDict["uid"]
    del verifierDict["uid"]
    conn.hset(f"userdata:verifiers:{uid}",mapping=verifierDict)


def get_data(conn, table_name, uid, key=None):
    res = None
    if key is None:
        res = conn.hgetall(f"userdata:{table_name}:{uid}")
        decoded = decode_dict(res)
        return decoded
    else:
        res = conn.hget(f"userdata:{table_name}:{uid}", key)
        return res


def disconnect(conn):
    conn.close()

if __name__=="__main__":
    conn = connect()
    # add_mentor(conn, {
    #     "uid": "johndoe",
    #     "name": "John Doe",
    #     "password": "password123",
    #     "section": "CSE-A"
    # })

    # d = get_data(conn, "mentors", "johndoe", "password")
    # print(d)

    r = redis.Redis(
        host="rediss://red-cj197btph6enmk10ro6g:6S2fDrVDrNHMUJH4oHaixPNfO8yQAkLV@singapore-redis.render.com:6379",
        port=6379,
        # password="6S2fDrVDrNHMUJH4oHaixPNfO8yQAkLV"
    )
    # print(r.set("hello","world"))
    print(r.get("hello"))



# if __name__ == "__main__":
#     r = redis.Redis(
#     host='redis-15709.c212.ap-south-1-1.ec2.cloud.redislabs.com',
#     port=15709,
#     password='256DnHtekLjXWyZptEh7HsgLRczCQ2xV')
#     # print(r.hgetall("userdata:students:22BD1A0505"))
#     # with open("FY.json") as f:

#     #     s = json.loads(f.read())
#     #     for i in s:
#     #         d = {
#     #             "firstname":i["firstname"][:-5],
#     #             "section": f'{i["dept"]}-{i["section"]}',
#     #             "picture":i["picture"],
#     #             "email": i["email"],
#     #             "phone":i["phone"]
#     #         }
#     #         r.hset(f"userdata:students:{i['hallticketno']}",mapping=d)
#     #         print(d)
        

        
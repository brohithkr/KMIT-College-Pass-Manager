import os
import hashlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVERURL = input("Enter the ServerURL: ")
KEY = input("Enter the key: ")
cspath = os.path.join(BASE_DIR,".configserver")

with open(cspath,"w") as cs:
    cs.write(f"SERVERURL = '{SERVERURL}'\n")
    cs.write(f"HKEY = '{hashlib.sha1(KEY.encode()).hexdigest()}'")


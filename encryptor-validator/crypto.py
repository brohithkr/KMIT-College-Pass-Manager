from Crypto.Cipher import AES
from Crypto.Signature import pkcs1_15
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from base64 import b64encode, b64decode
from hashlib import sha1

def pad(data: str, block_size: int) -> bytes:
    length = block_size - (len(data) % block_size)
    if length > 0:
        return data.encode() + (chr(length) * length).encode()
    else:
        return data.encode()

def depad(data: bytes) -> str:
    padding_length = data[-1]
    return data[:-padding_length].decode()

def AESencrypt(data: str, key: str) -> (str,str):
    cipher = AES.new(pad(key,AES.block_size),AES.MODE_CBC)
    encrypted_text = b64encode(cipher.encrypt(pad(data,AES.block_size))).decode()
    iv = b64encode(cipher.iv).decode()
    return encrypted_text, iv

def AESdecrypt(endata: str, key: str, iv: str) -> str:
    iv = b64decode(iv.encode())
    endata = b64decode(endata.encode())
    cipher = AES.new(pad(key,AES.block_size), AES.MODE_CBC, iv)
    decrypted_text = cipher.decrypt(endata)
    decrypted_text =  depad(decrypted_text)
    return decrypted_text

def RSAgenerate(passphrase):
    prikey = RSA.generate(1024)
    pubkey = prikey.public_key()

    return (prikey.export_key(passphrase=passphrase).decode(),pubkey.export_key().decode())

def signData(msg,prikey,passphrase):
    prikey = RSA.import_key(prikey.encode(),passphrase=passphrase)
    msgint = int.from_bytes(msg.encode(),byteorder="big")
    enmsgint = pow(msgint,prikey.d,prikey.n)
    enbytes = enmsgint.to_bytes((enmsgint.bit_length()+7)//8,"big")
    return b64encode(enbytes).decode()
    
def unsignData(signature,pubkey):
    pubkey = RSA.import_key(pubkey.encode())
    sigbytes = b64decode(signature.encode())
    sigint = int.from_bytes(sigbytes,"big")
    msgint = pow(sigint,pubkey.e,pubkey.n)
    msgbytes = msgint.to_bytes((msgint.bit_length()+7)//8,"big")
    msg = msgbytes.decode()
    return msg

def hashhex(s):
    return sha1(s.encode()).hexdigest()



if __name__=="__main__":
    prikey = RSA.generate(1024)
    pubkey = prikey.public_key()
    # print(type(prikey))
    # msg = b'Attack!'
    # hmsg = SHA1.new(msg)
    # print(hmsg.hexdigest())
    # cipher = pkcs1_15.new(prikey)
    # sig = cipher.sign(hmsg)
    # print(hmsg,sig)
    # cipher = pkcs1_15.new(pubkey)
    # try:
    #     print(cipher.verify(hmsg.digest(),sig))
    # except ValueError:
    #     print("Invalid Signature")

    # print(pubkey.export_key() in prikey.export_key())
    signature = signData("hello 1234",prikey.export_key(passphrase="hello").decode(),passphrase="hello")
    # print(b64encode(num.to_bytes((num.bit_length() + 7)//8,"big")))
    print(signature)
    msg = unsignData(signature,pubkey.export_key().decode())
    print(msg)

        
    

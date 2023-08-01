import cv2
from base64 import b64decode
import numpy as np



def scanQR(b64qr: str):
    qrbytesarray = np.asarray(bytearray(b64decode(b64qr.encode())),dtype="uint8")
    
    inputImage = cv2.imdecode(qrbytesarray,cv2.IMREAD_GRAYSCALE)
    qrDecoder = cv2.QRCodeDetector()
    data,bbox,rectifiedImage = qrDecoder.detectAndDecode(inputImage)
    if len(data)>0:
        return data
    else:
        return None

if __name__=="__main__":
    pass
    
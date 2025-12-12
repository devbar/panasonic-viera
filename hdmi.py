import panasonic_viera
import time
rc = panasonic_viera.RemoteControl("192.168.60.85", proxy='http://192.168.30.16:8118', app_id = "AV/K5XTaiKWmNg==", encryption_key = "u+KIbBB11GgV7ZtGZmb0wQ==")

info = rc.get_apps()
print(info)

#while True:
    # rc.send_key(panasonic_viera.Keys.HMDI_1)
    # time.sleep(5)
    #rc.send_key(panasonic_viera.Keys.HMDI_1)
    #time.sleep(5)
    # rc.send_key(panasonic_viera.Keys.HMDI_3)
    # time.sleep(5)
    # rc.send_key(panasonic_viera.Keys.HMDI_4)


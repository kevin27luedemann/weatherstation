import alarm
import time
import terminalio
import board
import busio
import struct
import displayio
import adafruit_bme680
import adafruit_ds3231
import adafruit_24lc32
import adafruit_requests
import wifi
import socketpool
import ipaddress
from secrets import secrets

#Define some important constants
URL         = "http://{}:8086/api/v2/write?org={}&bucket={}&precision=ns".format(secrets["server_ip"],secrets["influx_org"],secrets["influx_bucket"])

header      = {"Authorization": "Token {}".format(secrets["influx_token"]),
                "Content-Type": "text/plain; charset=utf-8",
                "Accept": "application/json"}
max_data    = 24
sleep_time  = 10
id_tag      = {"temp":0,
                "hum":1,
               "pres":2,
                "gas":3,
                "bat":4}

def packf(var):
    return struct.pack("f",var)

def unpackf(var):
    return struct.unpack("f",var)

def packb(var):
    return struct.pack("b",var)

def unpackb(var):
    return struct.unpack("b",var)

def index_pos(tag,hour,Bytse=4):
    global max_data
    return tag*max_data*Bytes+hour*Bytes

def slice_pos(tag,hour,Bytes=4):
    global max_data
    return slice(int(tag*max_data*Bytes+hour*Bytes),int(tag*max_data*Bytes+hour*Bytes+Bytes))

def count_pos(tag,hour,Bytes=4):
    global max_data
    return slice(tag*max_data*Bytes+hour,tag*max_data*Bytes+hour+1)

def get_max(tag,eep,Bytes=4):
    val     = unpackf(eep[slice_pos(tag,0,Bytes=Bytes)])
    for i in range(1,24):
        val = max(val,unpackf(eep[slice_pos(tag,i,Bytes=Bytes)]))
    return val

def get_min(tag,eep,Bytes=4):
    val     = unpackf(eep[slice_pos(tag,0,Bytes=Bytes)])
    for i in range(1,24):
        val = min(val,unpackf(eep[slice_pos(tag,i,Bytes=Bytes)]))
    return val

#Setup wifi
wifi.radio.connect(secrets["ssid"], secrets["password"])
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool)

#Set all I2C devices
i2c         = busio.I2C(board.SCL,board.SDA,frequency=100000)
bme         = adafruit_bme680.Adafruit_BME680_I2C(i2c)

#Initial read
for i in range(3):
    temp        = bme.temperature
    hum         = bme.humidity
    pres        = bme.pressure
    gas         = bme.gas
    time.sleep(1)
last_sec = time.monotonic()
while True:
    if last_sec+2 <= time.monotonic():
        last_sec = time.monotonic()
        #Read current state of device
        temp        = bme.temperature
        hum         = bme.humidity
        pres        = bme.pressure
        gas         = bme.gas

        data        = "{},sensor_id=BME680 temperature={},humidity={},pressure={},gas={} ".format(secrets["influx_name"],temp,hum,pres,gas)
        try:
            requests.post(URL,headers=header,data=data,timeout=2)
        except:
            print("post did not work")

        print(time.monotonic())
        print(data)

    time.sleep(0.1)


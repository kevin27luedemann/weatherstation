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
import analogio
import socketpool
import ipaddress
import countio
import digitalio
import microcontroller
import supervisor
from watchdog import WatchDogMode
from secrets import secrets

#Set watchdog
wd          = microcontroller.watchdog
wd.timeout  = 10
wd.mode     = WatchDogMode.RESET
wd.feed()

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

#Maximum count
ADC_max_cou     = 51931
#Voltage
ADC_max_vol     = 2.57
#mm of rain per count
bucket_content  = 0.2794
#Windspeed per count
speed_per_count=2/3

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

#speed in m/s
def get_wind_Speed(pin):
    start   = time.monotonic_ns()
    stop    = start
    while not(pin.value) and stop-start < 1e9:
        stop    = time.monotonic_ns()

    start   = time.monotonic_ns()
    stop    = start
    while pin.value and stop-start < 1e9:
        stop    = time.monotonic_ns()

    while not(pin.value) and stop-start < 3e9:
        stop    = time.monotonic_ns()

    if stop-start >= 3e9:
        return 0
    else:
        return 1/((stop-start)*1e-9)


#Setup wifi
try:
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    pool = socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool)
except:
    print("Some wrong with wind station")
    supervisor.reload()

wd.feed()
try:
    #Set all I2C devices
    i2c         = busio.I2C(board.SCL,board.SDA,frequency=100000)
    bme         = adafruit_bme680.Adafruit_BME680_I2C(i2c)
except:
    print("Some wrong with wind station")
    supervisor.reload()

wd.feed()
#Initial read
try:
    for i in range(3):
        temp        = bme.temperature
        hum         = bme.humidity
        pres        = bme.pressure
        gas         = bme.gas
        wd.feed()
        time.sleep(1)
except:
    print("Some wrong with wind station")
    supervisor.reload()

try:
    #Setup analog read
    wind_direction  = analogio.AnalogIn(board.A0)
    water_bucket    = countio.Counter(board.A2, edge=countio.Edge.RISE)
    wind_speed      = digitalio.DigitalInOut(board.A1)
    wind_speed.switch_to_input()
except:
    print("Some wrong with wind station")
    supervisor.reload()

wd.feed()
last_sec = time.monotonic()
while True:
    if last_sec+2 <= time.monotonic():
        try:
            last_sec = time.monotonic()
            if water_bucket.count > 0:
                bucket  = water_bucket.count
                water_bucket.reset()
            else:
                bucket  = 0
        except:
            print("Some wrong with wind station")
            supervisor.reload()
        try:
            rotation_rate   = get_wind_Speed(wind_speed)
            direction_volt  = wind_direction.value*ADC_max_vol/ADC_max_cou
        except:
            print("Some wrong with wind station")
            supervisor.reload()
        try:
            data2       = "{},sensor_id=wind_water direction_raw={},water_raw={},water_mm={},wind_raw={},wind_speed={}".format(secrets["influx_name"],direction_volt,bucket,bucket*bucket_content,rotation_rate,rotation_rate*speed_per_count)
        except:
            print("Some wrong with wind station")
            supervisor.reload()
        try:
            requests.post(URL,headers=header,data=data2,timeout=2)
        except:
            print("post did not work")
            supervisor.reload()

        #Read current state of device
        try:
            temp        = bme.temperature
            hum         = bme.humidity
            pres        = bme.pressure
            gas         = bme.gas
        except:
            print("I2C problems")
            supervisor.reload()

        try:
            data        = "{},sensor_id=BME680 temperature={},humidity={},pressure={},gas={} ".format(secrets["influx_name"],temp,hum,pres,gas)
        except:
            print("I2C problems")
            supervisor.reload()
        try:
            requests.post(URL,headers=header,data=data,timeout=2)
        except:
            print("post did not work")
            supervisor.reload()

        print(time.monotonic())
        print(data)
        print(data2)

    wd.feed()
    time.sleep(0.1)


from adafruit_magtag.magtag import MagTag
import alarm
import time
import terminalio
import board
import busio
import struct
import displayio
import adafruit_bme680
import adafruit_requests
import adafruit_ntp
import rtc
import wifi
import socketpool
import ipaddress
import supervisor
import microcontroller
from watchdog import WatchDogMode
from secrets import secrets

#Set watchdog
wd          = microcontroller.watchdog
wd.timeout  = 10
wd.mode     = WatchDogMode.RESET
wd.feed()


#Define some important constants
URL_send    = "http://{}:8086/api/v2/write?org={}&bucket={}&precision=ns".format(secrets["server_ip"],secrets["influx_org"],secrets["influx_bucket"])

URL_reci    = "http://{}:8086/api/v2/query?org={}".format(secrets["server_ip"],secrets["influx_org"])

temp_query  = 'from(bucket: "wetter") |> range(start: -5m) |> filter(fn: (r) => r["_measurement"] == "{}") |> filter(fn: (r) => r["_field"] == "temperature") |> aggregateWindow(every: 5m, fn: mean, createEmpty: false) |> yield(name: "mean")'

humi_query  = 'from(bucket: "wetter") |> range(start: -5m) |> filter(fn: (r) => r["_measurement"] == "{}") |> filter(fn: (r) => r["_field"] == "humidity") |> aggregateWindow(every: 5m, fn: mean, createEmpty: false) |> yield(name: "mean")'

pres_query  = 'from(bucket: "wetter") |> range(start: -5m) |> filter(fn: (r) => r["_measurement"] == "{}") |> filter(fn: (r) => r["_field"] == "pressure") |> aggregateWindow(every: 5m, fn: mean, createEmpty: false) |> yield(name: "mean")'

header_send = {"Authorization": "Token {}".format(secrets["influx_token"]),
                "Content-Type": "text/plain; charset=utf-8",
                "Accept": "application/json"}

header_reci = {"Authorization": "Token {}".format(secrets["influx_token"]),
                "Content-Type": "application/vnd.flux",
                "Accept": "application/csv"}

max_data    = 24
sleep_time  = 10
id_tag      = {"temp":0,
                "hum":1,
               "pres":2,
                "gas":3,
                "bat":4}

try:
    #Setup wifi
    wifi.radio.connect(secrets["ssid"], secrets["password"])
    pool = socketpool.SocketPool(wifi.radio)
    pool2= socketpool.SocketPool(wifi.radio)
    requests = adafruit_requests.Session(pool)
    wd.feed()

    ntp = adafruit_ntp.NTP(pool2,server=secrets["server_ip"],tz_offset=+2)
    print(ntp.datetime)
    rtc.RTC().datetime    = ntp.datetime

    wd.feed()
    #Set all I2C devices
    i2c         = busio.I2C(board.SCL,board.SDA,frequency=100000)
    bme         = adafruit_bme680.Adafruit_BME680_I2C(i2c)
except:
    print("Something went wrong during setup")
    supervisor.reload()
wd.feed()

#Setup MagTag
magtag = MagTag(rotation=90)

#Powersaving settings
magtag.peripherals.neopixels.fill((0,0,0))
magtag.peripherals.neopixels_disable    = True
magtag.peripherals.speaker_disable      = True

#Setup display
display     = magtag.display
group       = displayio.Group()

mid_x = magtag.graphics.display.width // 2 - 1
magtag.add_text( #Temperature inside
    text_font=terminalio.FONT,
    text_scale=2,
    text_position=(10,20),
    text_anchor_point=(0,0),
    is_data=False
)
magtag.add_text( #Humidity inside
    text_font=terminalio.FONT,
    text_position=(10,50),
    text_scale=2,
    text_anchor_point=(0,0),
    is_data=False
)
magtag.add_text( #Pressure inside
    text_font=terminalio.FONT,
    text_position=(10,80),
    text_scale=1,
    text_anchor_point=(0,0),
    is_data=False
)
magtag.add_text( #Temperature outside
    text_font=terminalio.FONT,
    text_position=(magtag.graphics.display.width-10,20),
    text_scale=2,
    text_anchor_point=(1,0),
    is_data=False
)
magtag.add_text( #Humidity outside
    text_font=terminalio.FONT,
    text_position=(magtag.graphics.display.width-10,50),
    text_scale=2,
    text_anchor_point=(1,0),
    is_data=False
)
magtag.add_text( #Pressure outside
    text_font=terminalio.FONT,
    text_position=(magtag.graphics.display.width-10,80),
    text_scale=1,
    text_anchor_point=(1,0),
    is_data=False
)
magtag.add_text( #Date and time
    text_font=terminalio.FONT,
    text_scale=2,
    text_position=(50,00),
    text_anchor_point=(0,0),
    is_data=False
)
wd.feed()

#Initial read
for i in range(3):
    temp        = bme.temperature
    hum         = bme.humidity
    pres        = bme.pressure
    gas         = bme.gas
    time.sleep(1)
    wd.feed()

def set_text():
    try:
        I_data  = requests.post(URL_reci,headers=header_reci,data=temp_query.format("esszimmer"),timeout=2).content
        I_data  = I_data.decode("ascii").split(",")
        temp_I      = float(I_data[-4])
    except:
        temp_I      = temp
    magtag.set_text("I {:.02f} C".format(temp_I),     auto_refresh = False,index=0)

    try:
        I_data  = requests.post(URL_reci,headers=header_reci,data=humi_query.format("esszimmer"),timeout=2).content
        I_data  = I_data.decode("ascii").split(",")
        hum_I       = float(I_data[-4])
    except:
        hum_I       = hum
    magtag.set_text("I {:.02f} %".format(hum_I),      auto_refresh = False,index=1)

    try:
        I_data  = requests.post(URL_reci,headers=header_reci,data=pres_query.format("esszimmer"),timeout=2).content
        I_data  = I_data.decode("ascii").split(",")
        pres_I      = float(I_data[-4])
    except:
        pres_I      = pres
    magtag.set_text("I {:.01f} hPa".format(pres_I),   auto_refresh = False,index=2)

    try:
        A_data  = requests.post(URL_reci,headers=header_reci,data=temp_query.format("draussen"),timeout=2).content
        A_data  = A_data.decode("ascii").split(",")
        temp_A      = float(A_data[-4])
    except:
        temp_A      = -273.0
    magtag.set_text("A {:.02f} C".format(temp_A),     auto_refresh = False,index=3)

    try:
        A_data  = requests.post(URL_reci,headers=header_reci,data=humi_query.format("draussen"),timeout=2).content
        A_data  = A_data.decode("ascii").split(",")
        hum_A       = float(A_data[-4])
    except:
        hum_A       = 0.0
    magtag.set_text("A {:.02f} %".format(hum_A),      auto_refresh = False,index=4)

    try:
        A_data  = requests.post(URL_reci,headers=header_reci,data=pres_query.format("draussen"),timeout=2).content
        A_data  = A_data.decode("ascii").split(",")
        pres_A      = float(A_data[-4])
    except:
        pres_A      = 0.0
    magtag.set_text("A {:.01f} hPa".format(pres_A),   auto_refresh = False,index=5)

    now         = rtc.RTC().datetime
    magtag.set_text("{:02d}.{:02d}.{:d} {:02d}:{:02d}".format(now.tm_mday,now.tm_mon,now.tm_year,now.tm_hour,now.tm_min),   auto_refresh = False,index=6)

set_text()
magtag.refresh()

last_sec    = time.monotonic()

wd.feed()
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
            requests.post(URL_send,headers=header_send,data=data,timeout=2)
        except:
            print("HTTP POST went wrong")
            supervisor.reload()

        #write the data to display
        if  rtc.RTC().datetime.tm_sec >= 0 and \
            rtc.RTC().datetime.tm_sec <= 2:
            set_text()
            magtag.refresh()

        print(time.monotonic(),data)

    wd.feed()
    time.sleep(0.1)


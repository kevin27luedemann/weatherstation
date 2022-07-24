from adafruit_magtag.magtag import MagTag
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
import supervisor
from secrets import secrets

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
    requests = adafruit_requests.Session(pool)

    #Set all I2C devices
    i2c         = busio.I2C(board.SCL,board.SDA,frequency=100000)
    bme         = adafruit_bme680.Adafruit_BME680_I2C(i2c)

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

    #Initial read
    for i in range(3):
        temp        = bme.temperature
        hum         = bme.humidity
        pres        = bme.pressure
        gas         = bme.gas
        time.sleep(1)

    I_data  = requests.post(URL_reci,headers=header_reci,data=temp_query.format("esszimmer"),timeout=2).content
    I_data  = I_data.decode("ascii").split(",")
    magtag.set_text("I {:.02f} C".format(float(I_data[-4])),     auto_refresh = False,index=0)

    I_data  = requests.post(URL_reci,headers=header_reci,data=humi_query.format("esszimmer"),timeout=2).content
    I_data  = I_data.decode("ascii").split(",")
    magtag.set_text("I {:.02f} %".format(float(I_data[-4])),      auto_refresh = False,index=1)
    I_data  = requests.post(URL_reci,headers=header_reci,data=pres_query.format("esszimmer"),timeout=2).content
    I_data  = I_data.decode("ascii").split(",")
    magtag.set_text("I {:.01f} hPa".format(float(I_data[-4])),   auto_refresh = False,index=2)

    A_data  = requests.post(URL_reci,headers=header_reci,data=temp_query.format("draussen"),timeout=2).content
    A_data  = A_data.decode("ascii").split(",")
    magtag.set_text("A {:.02f} C".format(float(A_data[-4])),     auto_refresh = False,index=3)

    A_data  = requests.post(URL_reci,headers=header_reci,data=humi_query.format("draussen"),timeout=2).content
    A_data  = A_data.decode("ascii").split(",")
    magtag.set_text("A {:.02f} %".format(float(A_data[-4])),      auto_refresh = False,index=4)

    A_data  = requests.post(URL_reci,headers=header_reci,data=pres_query.format("draussen"),timeout=2).content
    A_data  = A_data.decode("ascii").split(",")
    magtag.set_text("A {:.01f} hPa".format(float(A_data[-4])),   auto_refresh = False,index=5)

    magtag.refresh()

    last_sec    = time.monotonic()
    last_disp   = time.monotonic()

    while True:
        if last_sec+2 <= time.monotonic():
            last_sec = time.monotonic()
            #Read current state of device
            temp        = bme.temperature
            hum         = bme.humidity
            pres        = bme.pressure
            gas         = bme.gas

            data        = "{},sensor_id=BME680 temperature={},humidity={},pressure={},gas={} ".format(secrets["influx_name"],temp,hum,pres,gas)
            requests.post(URL_send,headers=header_send,data=data,timeout=2)

            #write the data to display
            if time.monotonic()>= last_disp+120:
                I_data  = requests.post(URL_reci,headers=header_reci,data=temp_query.format("esszimmer"),timeout=2).content
                I_data  = I_data.decode("ascii").split(",")
                magtag.set_text("I {:.02f} C".format(float(I_data[-4])),     auto_refresh = False,index=0)

                I_data  = requests.post(URL_reci,headers=header_reci,data=humi_query.format("esszimmer"),timeout=2).content
                I_data  = I_data.decode("ascii").split(",")
                magtag.set_text("I {:.02f} %".format(float(I_data[-4])),      auto_refresh = False,index=1)
                I_data  = requests.post(URL_reci,headers=header_reci,data=pres_query.format("esszimmer"),timeout=2).content
                I_data  = I_data.decode("ascii").split(",")
                magtag.set_text("I {:.01f} hPa".format(float(I_data[-4])),   auto_refresh = False,index=2)

                A_data  = requests.post(URL_reci,headers=header_reci,data=temp_query.format("draussen"),timeout=2).content
                A_data  = A_data.decode("ascii").split(",")
                magtag.set_text("A {:.02f} C".format(float(A_data[-4])),     auto_refresh = False,index=3)

                A_data  = requests.post(URL_reci,headers=header_reci,data=humi_query.format("draussen"),timeout=2).content
                A_data  = A_data.decode("ascii").split(",")
                magtag.set_text("A {:.02f} %".format(float(A_data[-4])),      auto_refresh = False,index=4)

                A_data  = requests.post(URL_reci,headers=header_reci,data=pres_query.format("draussen"),timeout=2).content
                A_data  = A_data.decode("ascii").split(",")
                magtag.set_text("A {:.01f} hPa".format(float(A_data[-4])),   auto_refresh = False,index=5)
                last_disp   = time.monotonic()
                magtag.refresh()

            print(time.monotonic())
            print(data)

        time.sleep(0.1)

except:
    supervisor.reload()


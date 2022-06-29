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

#Define some important constants
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

#Wake up alarm on Pin A
BA_alarm    = alarm.pin.PinAlarm(board.BUTTON_A,value=False,pull=True)

#Setup wifi
from secrets import secrets
wifi.radio.connect(secrets["ssid"], secrets["password"])
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool)
TEXT_URL = "http://wifitest.adafruit.com/testwifi/index.html"

#Set all I2C devices
i2c         = busio.I2C(board.SCL,board.SDA,frequency=100000)
bme         = adafruit_bme680.Adafruit_BME680_I2C(i2c)
hw_rtc      = adafruit_ds3231.DS3231(i2c)
#Set time
#hw_rtc.datetime = time.struct_time((2022, 4, 4, 12, 43, 40, 0, 94, 1))

#EEPROM
eeprom = adafruit_24lc32.EEPROM_I2C(i2c,address=0x57)

#Setup MagTag
magtag = MagTag()

#Powersaving settings
magtag.peripherals.neopixels.fill((0,0,0))
magtag.peripherals.neopixels_disable    = True
magtag.peripherals.speaker_disable      = True

#Setup display
display     = magtag.display
group       = displayio.Group()

#Read current state of device
now         = hw_rtc.datetime
temp        = bme.temperature
hum         = bme.humidity
pres        = bme.pressure
gas         = bme.gas
bat         = magtag.peripherals.battery

URL         = "http://192.168.2.119:8086/api/v2/write?org={}&bucket={}&precision=ns".format(secrets["influx_org"],secrets["influx_bucket"])

header      = {"Authorization": "Token {}".format(secrets["influx_token"]),
                "Content-Type": "text/plain; charset=utf-8",
                "Accept": "application/json"}
data        = "magtag,sensor_id=BME688 temperature={},humidity={},pressure={},gas={},bat={} ".format(temp,hum,pres,gas,bat)
try:
    requests.post(URL,headers=header,data=data)
except:
    print("post did not work")

print(now)
print(temp)
print(hum)
print(pres)
print(gas)
print(bat)

if now.tm_min <= sleep_time/60.:
    eeprom[slice_pos(id_tag["temp"],int(now.tm_hour))]  = packf(temp)
    eeprom[slice_pos(id_tag["hum"], int(now.tm_hour))]  = packf(hum)
    eeprom[slice_pos(id_tag["pres"],int(now.tm_hour))]  = packf(pres)
    eeprom[slice_pos(id_tag["gas"], int(now.tm_hour))]  = packf(gas)
    eeprom[slice_pos(id_tag["bat"], int(now.tm_hour))]  = packf(bat)

mid_x = magtag.graphics.display.width // 2 - 1
magtag.add_text( #Battery
    text_font=terminalio.FONT,
    text_position=(10,0),
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.add_text( #Datetime
    text_font=terminalio.FONT,
    text_position=(magtag.graphics.display.width-10,0),
    text_anchor_point=(1,0),
    is_data=False,
)
magtag.add_text( #Temperature
    text_font=terminalio.FONT,
    text_position=(10,10),
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.add_text( #Humidity
    text_font=terminalio.FONT,
    text_position=(magtag.graphics.display.width-10,10),
    text_anchor_point=(1,0),
    is_data=False,
)
magtag.add_text( #Pressure
    text_font=terminalio.FONT,
    text_position=(10,20),
    text_anchor_point=(0,0),
    is_data=False,
)
magtag.add_text( #Gas
    text_font=terminalio.FONT,
    text_position=(magtag.graphics.display.width-10,20),
    text_anchor_point=(1,0),
    is_data=False,
)

magtag.set_text("{}.{}.{} {:02}:{:02}:{:02}".format(now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec),                auto_refresh = False,index=1)
magtag.set_text("Battery     = {:.02f} V".format(bat),      auto_refresh = False,index=0)
magtag.set_text("Temperature = {:.02f} C".format(temp),     auto_refresh = False,index=2)
magtag.set_text("Humidity =   {:.02f} %".format(hum),       auto_refresh = False,index=3)
magtag.set_text("Pressure    = {:.01f} hPa".format(pres),   auto_refresh = False,index=4)
magtag.set_text("Gas  = {:d} Ohm".format(int(gas)),         auto_refresh = False,index=5)

#display.show(group)

magtag.refresh()

if isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
    magtag.peripherals.neopixels_disable    = False
    magtag.peripherals.neopixels.fill((127,63,63))
    time.sleep(10)

alarm.exit_and_deep_sleep_until_alarms(alarm.time.TimeAlarm(monotonic_time=time.monotonic() + sleep_time),  
                                        BA_alarm
                                        )

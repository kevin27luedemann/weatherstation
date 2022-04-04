from adafruit_magtag.magtag import MagTag
import alarm
import time
import terminalio
import board
import busio
import struct
import adafruit_bme680
import adafruit_ds3231
import adafruit_24lc32

max_data    = 24

#Wake up alarm on Pin A
BA_alarm    = alarm.pin.PinAlarm(board.BUTTON_A,value=False,pull=True)

#Set all I2C devices
i2c         = busio.I2C(board.SCL,board.SDA,frequency=100000)
bme         = adafruit_bme680.Adafruit_BME680_I2C(i2c)
hw_rtc      = adafruit_ds3231.DS3231(i2c)

#EEPROM
eeprom = adafruit_24lc32.EEPROM_I2C(i2c,address=0x57)

print("length: {}".format(len(eeprom)))

#print(eeprom[0])

#Set time
#hw_rtc.datetime = time.struct_time((2022, 4, 4, 12, 43, 40, 0, 94, 1))

#Read current state of device
now         = hw_rtc.datetime
now_st      = struct.pack("bbbb",now.tm_year-2000,now.tm_mon,now.tm_mday,now.tm_hour)
temp        = bme.temperature
hum         = bme.humidity
pres        = bme.pressure
gas         = bme.gas

print(now_st)
data        = struct.pack("f",temp)
#eeprom[0:4] = now_st
print(data)
da          = eeprom[0:4]
print(da)
print(struct.unpack("bbbb",da))

print(now)
print(temp)
print(hum)
print(pres)
print(gas)

magtag = MagTag()
magtag.peripherals.neopixels.fill((0,0,0))
magtag.peripherals.neopixels_disable    = True

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

magtag.set_text("Battery     = {:.02f} V".format(magtag.peripherals.battery), auto_refresh = False,index=0)
magtag.set_text("{}.{}.{} {:02}:{:02}:{:02}".format(now.tm_mday, now.tm_mon, now.tm_year, now.tm_hour, now.tm_min, now.tm_sec),                auto_refresh = False,index=1)
magtag.set_text("Temperature = {:.02f} C".format(temp),     auto_refresh = False,index=2)
magtag.set_text("Humidity =   {:.02f} %".format(hum),       auto_refresh = False,index=3)
magtag.set_text("Pressure    = {:.01f} hPa".format(pres),   auto_refresh = False,index=4)
magtag.set_text("Gas  = {:d} Ohm".format(int(gas)),         auto_refresh = False,index=5)

magtag.refresh()

if isinstance(alarm.wake_alarm, alarm.pin.PinAlarm):
    magtag.peripherals.neopixels_disable    = False
    magtag.peripherals.neopixels.fill((127,63,63))
    time.sleep(10)

alarm.exit_and_deep_sleep_until_alarms(alarm.time.TimeAlarm(monotonic_time=time.monotonic() + 120),  
                                        BA_alarm
                                        )

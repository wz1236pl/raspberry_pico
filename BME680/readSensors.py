import uos
import network
import socket
import machine
import utime
import struct
import requests
import gc
from machine import Pin, I2C
from bme680 import *

ssid = 'ZYGAR_T_DOM'
password = '000000FA49'

print("Machine: \t" + uos.uname()[4])
print("MicroPython: \t" + uos.uname()[3])

NTP_DELTA = 2208988800
host = "pool.ntp.org"

rtc=machine.RTC()

def set_time():
    # Get the external time reference
    NTP_QUERY = bytearray(48)
    NTP_QUERY[0] = 0x1B
    addr = socket.getaddrinfo(host, 123)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(1)
        res = s.sendto(NTP_QUERY, addr)
        msg = s.recv(48)
    finally:
        s.close()

    #Set our internal time
    val = struct.unpack("!I", msg[40:44])[0]
    tm = val - NTP_DELTA    
    t = time.gmtime(tm)
    rtc.datetime((t[0],t[1],t[2],t[6]+1,t[3],t[4],t[5],0))

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    
try:
    connect()
except KeyboardInterrupt:
    machine.reset()

set_time()
    
headers = {
    'identity_key': 'c956c302086a042dd0426b4e62652273e05a6ce74d0b77f8b5602e0811025066'
}
urlTemp = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Temp'
urlHumi = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Humi'
urlPres = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Pres'

i2c=I2C(1,sda=Pin(2), scl=Pin(3), freq=400000)    #initializing the I2C method
bme = BME680_I2C(i2c=i2c)

sendAfter = 0

while True:
    if (utime.mktime(rtc.datetime()) > sendAfter):
        if (rtc.datetime()[5] % 5 != 0):
            continue
        timestamp = utime.mktime(rtc.datetime())
        temperature = str(round(bme.temperature, 2))
        humidity = str(round(bme.humidity, 2))
        pressure = str(round(bme.pressure, 2))
        gas = str(round(bme.gas/1000, 2))
        date = utime.localtime(timestamp)
        formatted_date_time = "{:02d}/{:02d}/{:04d}T{:02d}:{:02d}:{:02d}".format(
            date[2],  # day
            date[1],  # month
            date[0],  # year
            date[4]+1,  # hour
            date[5],  # minute
            date[6]   # second
        )
    

        print('-------------------------')
        print('Date:', formatted_date_time)
        print('Temperature:', temperature, 'C')
        print('Humidity:', humidity, ' %')
        print('Pressure:', pressure, ' hPa')
        print('Gas:', gas, ' KOhms')
        print('Temperature HttpStatus:', requests.put(url, json={"observations": [{ "value": temperature}]}, headers=headers).status_code)
        print('Humidity HttpStatus:', requests.put(url, json={"observations": [{ "value": humidity}]}, headers=headers).status_code)
        print('Pressure HttpStatus:', requests.put(url, json={"observations": [{ "value": pressure}]}, headers=headers).status_code)
        
        sendAfter = 0 + timestamp
    
    


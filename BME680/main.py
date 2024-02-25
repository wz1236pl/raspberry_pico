import uos
import network
import socket
import machine
import utime
import struct
import requests
from machine import Pin, I2C
from bme680 import *

ssid = 'ZYGAR_T_DOM'
password = '000000FA49'

NTP_DELTA = 2208988800
host = "pool.ntp.org"

rtc=machine.RTC()

def set_time():
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

    val = struct.unpack("!I", msg[40:44])[0]
    tm = val - NTP_DELTA    
    t = time.gmtime(tm)
    rtc.datetime((t[0],t[1],t[2],t[6]+1,t[3],t[4],t[5],0))

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        utime.sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    
try:
    connect()
except KeyboardInterrupt:
    machine.reset()

set_time()
    
sentiloHeaders = {
    'identity_key': 'KrosnoSentilo'
}

sprnigHeaders = {
    'API-KEY': 'KrosnoSpring'
}

urlTemp = 'http://iot.kpu.krosno.pl:8080/data/INZ/BME680Temp'
urlHumi = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Humi'
urlPres = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Pres'
urlSpring = 'http://iot.kpu.krosno.pl:8082/api/add/many'

i2c=I2C(1,sda=Pin(2), scl=Pin(3), freq=400000)
bme = BME680_I2C(i2c=i2c)

led = machine.Pin("LED", machine.Pin.OUT)
led.on()

sendAfter = 0

while True:
    if (utime.mktime(rtc.datetime()) > sendAfter):
        if (rtc.datetime()[5] % 10 != 0):
            continue
        timestamp = utime.mktime(rtc.datetime())
        temperature = str(round(bme.temperature, 2))
        humidity = str(round(bme.humidity, 2))
        pressure = str(round(bme.pressure, 2))
        gas = str(round(bme.gas/1000, 2))
        date = utime.localtime(timestamp)
        formatted_date_time = "{:02d}/{:02d}/{:04d}T{:02d}:{:02d}:{:02d}".format(
            date[2],  	# day
            date[1],  	# month
            date[0],  	# year
            date[4]+1,  # hour
            date[5],  	# minute
            0   		# second
        )
        print("sending")
        try:
            requests.put(urlTemp, json={"observations": [{ "value": temperature, "timestamp": formatted_date_time}]}, headers=sentiloHeaders)
            requests.put(urlHumi, json={"observations": [{ "value": humidity, "timestamp": formatted_date_time}]}, headers=sentiloHeaders)
            requests.put(urlPres, json={"observations": [{ "value": pressure, "timestamp": formatted_date_time}]}, headers=sentiloHeaders)
        except:
            print("An exception occurred when sending data to Sentilo")

        try:    
            requests.post(urlSpring, json={"readingsList": [
            {"sensorType": "TEMPERATURE","sensorName": "BME680","reading": temperature,"timestamp": formatted_date_time,"outdoor": True},
            {"sensorType": "PRESSURE","sensorName": "BME680","reading": pressure,"timestamp": formatted_date_time,"outdoor": True},
            {"sensorType": "HUMIDITY","sensorName": "BME680","reading": humidity,"timestamp": formatted_date_time,"outdoor": True}
            ]}, headers=sprnigHeaders)
        except:
            print("An exception occurred when sending data to SpringBoot")
        sendAfter = 0 + timestamp
            

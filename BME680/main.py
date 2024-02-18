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
    'identity_key': '21ded40eae01a39bcd19407ffc25bba233495e827df02313d0fe0a9c69553822'
}

sprnigHeaders = {
    'API-KEY': 'krosno'
}

urlTemp = 'http://iot.kpu.krosno.pl:8080/data/INZ/BME680Temp'
urlHumi = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Humi'
urlPres = 'http://iot.kpu.krosno.pl:8081/data/INZ/BME680Pres'
urlSpring = 'http://192.168.55.109:8080/api/add/many'

i2c=I2C(1,sda=Pin(2), scl=Pin(3), freq=400000)    #initializing the I2C method
bme = BME680_I2C(i2c=i2c)

sendAfter = 0

while True:
    if (rtc.datetime()[5] % 30 != 0):
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

    print('-------------------------')
    print('Date:', formatted_date_time)
    print('Temperature:', temperature, 'C')
    print('Humidity:', humidity, ' %')
    print('Pressure:', pressure, ' hPa')
    print('Gas:', gas, ' KOhms')
    try:
        print('Temperature Sentilo HttpStatus:', requests.put(urlTemp, data={"observations": [{ "value": temperature}]}, headers=headers).status_code)
        print('Humidity Sentilo HttpStatus:', requests.put(urlHumi, json={"observations": [{ "value": humidity, "timestamp": formatted_date_time}]}, headers=headers).status_code)
        print('Pressure Sentilo HttpStatus:', requests.put(urlPres, json={"observations": [{ "value": pressure, "timestamp": formatted_date_time}]}, headers=headers).status_code)
    except:
        print("An exception occurred when sending data to Sentilo")
    try:    
        print('Spring HttpStatus:', requests.post(urlSpring, json={"readingsList": [
        {"sensorType": "TEMPERATURE","sensorName": "BME680","reading": temperature,"timestamp": formatted_date_time,"outdoor": True},
        {"sensorType": "PRESSURE","sensorName": "BME680","reading": humidity,"timestamp": formatted_date_time,"outdoor": True},
        {"sensorType": "HUMIDITY","sensorName": "BME680","reading": pressure,"timestamp": formatted_date_time,"outdoor": True}
        ]}, headers=sprnigHeaders).status_code)
    except:
        print("An exception occurred when sending data to SpringBoot")

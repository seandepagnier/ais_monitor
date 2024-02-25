#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import time
import network
import machine
import asyncio

ssid="mars"
psk="rmyu030/"
nmea_port = 20220

#Connect to WLAN
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, psk)

# resolve ais_monitor.local to our ip address
from mdns_client import Client
from mdns_client.responder import Responder

client = Client('0.0.0.0')
responder = Responder(
    client,
    own_ip=lambda: wlan.ifconfig()[0],
    host=lambda: "ais_monitor"
)

responder.advertise("_nmea", "_tcp", port=nmea_port)

writers = []
async def serve_nmea():
    async def handle_request(reader, writer):
        print('nmea client connected', writer)
        writers.append(writer)
        while writer in writers:
            try:
                # do not use incomming data, simply discard it                
                await reader.read(1024)
            except Exception as e:
                break

        print('nmea client lost', writer)
        writers.remove(writer)
        await writer.aclose()

    print('nmea server loading...')
    try:
        server = await asyncio.start_server(handle_request, host='0.0.0.0', port=nmea_port)
        await asyncio.sleep(1)
        print('nmea server started')
        await server.wait_closed()
    except Exception as e:
        print('server exception', e)

    print('nmea server exited')
    machine.reset()

async def write_nmea(line):
    lwriters = list(writers)
    for writer in lwriters:
        try:
            await writer.awrite(line)
        except Exception as e:
            print("exception writing to writer", e, writer)
            writers.remove(writer)
    print(line.strip())

async def maintain_connection():
    while True:
        t0 = time.ticks_ms()
        if not wlan.isconnected():
            while not wlan.isconnected():
                s = wlan.status()
                print('connecting...', s)
                if s == -1 or time.ticks_ms() - t0 > 10*1000:
                    wlan.connect(ssid, psk)

                await asyncio.sleep(1)
            print('connected', wlan.ifconfig())
        await asyncio.sleep(3)
    

# for testing, simply serve ais messages on tcp
def main():
    from machine import UART, Pin
    from non_blocking_readline import non_blocking_readline
    
    uart0 = UART(0, baudrate=38400, tx=Pin(0), rx=Pin(1))
    uart0.init(bits=8, parity=None, stop=1, timeout=0)

    async def read_nmea():
        print('reading from nmea')
        while True:
            line = non_blocking_readline(uart0)
            if line:
                await write_nmea(line)
                print("read line", line.strip(), len(line))
            else:
                await asyncio.sleep(1)
    
    
    loop = asyncio.get_event_loop()
    loop.create_task(serve_nmea())
    loop.create_task(read_nmea())
    loop.create_task(maintain_connection())
    loop.run_forever()

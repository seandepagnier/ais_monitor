#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  


import asyncio
from microdot import Microdot, Response, send_file
from microdot.websocket import with_websocket
from microdot.utemplate import Template

import wireless
import config

app = Microdot()

rotations = 3 # messages will timeout after 3 rotations
nmea_messages = list(map(lambda x : {}, range(rotations)))
last_gps_nmea = None
current5 = rotations

Response.default_content_type = 'text/html'

websockets = []

@app.route('/ws')
@with_websocket
async def websocket(request, ws):
    print('got new websocket', ws, request)
    websockets.append(ws)
    # send backlog of recent unique nmea messages to new connections
    if last_gps_nmea:
        ws.send(last_gps_nmea)
    for nmeas in nmea_messages:
        for nmea in nmeas:
            ws.send(nmea)
    while True:
        data = await ws.receive()

@app.route('/', methods=['GET', 'POST'])
async def index(req):
    name = None
    if req.method == 'POST':
        c = config.config
        needwrite = False
        for name in c:
            value = req.form.get(name)
            if c[name] != value:
                c[name] = value
                if name in ['ssid', 'psk']:
                    wireless.reset()
                needwrite = True
        if needwrite:
            config.write()

    return Template('index.html').render(config=c)

@app.route('/<path:path>')
async def static(request, path):
    if '..' in path:
        # directory traversal is not allowed
        return 'Not found', 404
    return send_file('static/' + path)

async def serve():
    try:
        await app.start_server(port=80, debug=True)
    except Exception as e:
        print("CAUGHT EXCEPTION server!!", e)
        import machine
        machine.reset()

async def ais_data(ais_data, nmeas):
    for nmea in nmeas:
        for ws in list(websockets):
            try:
                await ws.send(nmea)
            except Exception as e:
                print('except sending to websocket', e, ws)
                websockets.remove(ws)
                
    # store each unique mmsi and message type
    key = (ais_data['message_type'], ais_data['mmsi'])
    for rotation in range(1, rotations):
        if key in nmea_messages:
            del nmea_messages[rotation][key] # remove old entree
    nmea_messages[0][key] = nmeas # store most recent

    # find which 5 minute index we are currently
    minute5 = ais_data['ticks_ms'] / 1000 / 60 / 5
    global current5
    if minute5 > current5:  # if we rolled over?
        current5 = minute5
        nmea_messages.pop() # remove stale messages
        nmea_messages.insert(0, {})

def gps_data(nmea):
    global last_gps_nmea
    last_gps_nmea = gps_data

# for testing
def main():
    import network, time
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    c = config.config
    wlan.connect(c['ssid'], c['psk'])

    while not wlan.isconnected():
        print("connecting....", wlan.status())
        time.sleep(1)
    print(wlan.ifconfig())

    ap = network.WLAN(network.AP_IF)
    ap.config(ssid='picow', password='encryptme')
    ap.active(True)
    while ap.active() == False:
        pass

    print(ap.ifconfig())
    
    loop = asyncio.get_event_loop()
    loop.create_task(serve())
    loop.run_forever()

#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  


import asyncio
from microdot import Microdot, Response
from microdot.utemplate import Template

import alarm

app = Microdot()

Response.default_content_type = 'text/html'

ssid="mars"
psk="rmyu030/"

@app.route('/', methods=['GET', 'POST'])
async def index(req):
    global ssid, psk
    name = None
    if req.method == 'POST':
        ssid = req.form.get('ssid')
        psk = req.form.get('psk')

        c = alarm.config
        c['muted'] = req.form.get('muted')
        c['proximity_dist'] = req.form.get('proximity_dist')
        c['tcpa_time'] = req.form.get('tcpa_time')
        c['tcpa_dist'] = req.form.get('tcpa_dist')

        print('ssid', ssid, psk)
    return Template('index.html').render(ssid=ssid, psk=psk)

async def serve():
    try:
        await app.start_server(port=80, debug=True)
    except Exception as e:
        print("CAUGHT EXCEPTION server!!", e)
        import machine
        machine.reset()

nmea_lines = {}
rotations = 3 # messages will timeout after 3 rotations
nmea_messages = list(map(lambda x : {}, range(rotations)))
current5 = rotations

def ais_data(ais_data, nemas):
    # store each unique mmsi and message type
    key = (ais_data['message_type'], ais_data['mmsi'])
    nmea_lines[key] = nemas # store nmea messages
    for rotation in range(1, rotations):
        if key in nmea_messages:
            del nmea_messages[rotation][key] # unmark old entree
    nmea_messages[0][key] = True # mark as most recent

    # find which 5 minute index we are currently
    minute5 = ais_data['ticks_ms'] / 1000 / 60 / 5
    global current5
    if minute5 > current5:  # if we rolled over?
        current5 = minute5
        rkeys = nmea_messages.pop()
        nmea_messages = [{} + nmea_messages]
        for key in rkeys:
            del nmea_lines[key] # remove stale messages

def gps_data(gps_data):
    pass

# for testing
def main():
    import network, time
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, psk)

    while not wlan.isconnected():
        print("connecting....", wlan.status())
        time.sleep(1)
    print(wlan.ifconfig())

    ap = network.WLAN(network.AP_IF)
    ap.config(essid='picow', password='encryptme')
    ap.active(True)
    while ap.active() == False:
        pass

    print(ap.ifconfig())
    
    loop = asyncio.get_event_loop()
    loop.create_task(serve())
    loop.run_forever()

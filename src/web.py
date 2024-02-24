#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  


import asyncio
from microdot import Microdot, Response
from microdot.utemplate import Template
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
        print('ssid', ssid, psk)
    print('ssid2', ssid, psk)
    return Template('index.html').render(ssid=ssid, psk=psk)

async def serve():
    try:
        await app.start_server(debug=True)
    except Exception as e:
        print("CAUGHT EXCEPTION server!!", e)
        import machine
        machine.reset()

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

main()

#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import time, math, os
import machine, gc, micropython

from decode_ais import decode_ais
from decode_gps import decode_gps
from alarm import compute_alarm
from non_blocking_readline import non_blocking_readline
import wireless
import leds
import web

# this pin is used for a button that mutes the alarm
mute_button = machine.Pin(12, machine.Pin.PULL_UP)

gps_data = None
ships = {}
ships_led_time = 0

# initialize uart0 to receive ais data at 38400 baud
uart0 = machine.UART(0, baudrate=38400, tx=machine.Pin(0), rx=machine.Pin(1))
uart0.init(bits=8, parity=None, stop=1, timeout=0)

# initialize uart1 to receive gps messages at 4800 baud
uart1 = machine.UART(0, baudrate=38400, tx=machine.Pin(4), rx=machine.Pin(5))
uart1.init(bits=8, parity=None, stop=1, timeout=0)


async def iteration():
    t = time.ticks_ms()
    # receive ais data
    ais_line = non_blocking_readline(uart0)
    if ais_line:
        await wireless.write_nmea(ais_line)
        ais_data = decode_ais(ais_line)
        if ais_data:
            ships[ais_data['mmsi']] = ais_data
            leds.on_timeout('ais')
            compute_alarm(ais_data)

    # receive gps data
    gps_line = non_blocking_readline(uart1)
    if gps_line:
        await wireless.write_nmea(gps_line)
        gps_data = decode_gps(gps_line)
        if gps_data:
            leds.on_timeout('gps', 10)

    # flash ships led based on closest ship
    # once per second for 1 mile,  once every 10 seconds if 10 miles
    if t > ships_led_time:
        mindist = 10
        for mmsi in list(ships):
            t0, ts = ship[mmsi]['ts']
            if t - t0 > 600:  # timeout after 10 minutes
                del ships[mmsi]
            else:
                dist = ship[mmsi]['dist']
                mindist = min(mindist, dist)
        if mindist < 10:
            leds.on_timeout('ships')
        ships_led_time = t+mindist*1000

    # check mute button to toggle mute function
    if not mute_button.value():
        if t-mute_toggle_time > 1:
            muted = not muted
            mute_toggle_time = t
        led_on('mute', muted)

    # turn off leds that timed out
    leds.timeout(t)
        
    # sleep for remainder of second
    await asyncio.sleep_ms(max(1000-time.ticks_ms()+t, 0))

wdt = machine.WDT(timeout=8000)  # enable it with a timeout of 8s

async def feed_watchdog():
    while True:
        wdt.feed()
        await asyncio.sleep(3)


async def report_statistics():
    while True:
        F = gc.mem_free()
        A = gc.mem_alloc()
        print('mem stat', F, A)
        s = os.statvfs('/')
        print(f"Free storage: {s[0]*s[3]/1024} KB")
        micropython.mem_info()
        await asyncio.sleep(10)

leds.value('pwr', True)


# create tasks
loop = asyncio.get_event_loop()
loop.create_task(iteration())
loop.create_task(report_statistics())
loop.create_task(wireless.serve_nmea())
loop.create_task(wireless.maintain_connection())
loop.create_task(web.serve())
loop.create_task(feed_watchdog())
loop.run_forever()

print('finished main loop??')
machine.reset()

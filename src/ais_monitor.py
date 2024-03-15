#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import time, math, os
starttime = time.ticks_ms()


import asyncio
import machine, gc, micropython

from decode_ais import decode_ais
from decode_gps import decode_gps
import alarm
from non_blocking_readline import non_blocking_readline
import wireless
import leds
import web

# these pins are used for buttons
buttons = {'mute': machine.Pin(12, machine.Pin.PULL_UP),
           'anchor': machine.Pin(18, machine.Pin.PULL_UP),
           'ap': machine.Pin(20, machine.Pin.PULL_UP)}

# initialize uart0 to receive ais data at 38400 baud
uart0 = machine.UART(0, baudrate=38400, tx=machine.Pin(0), rx=machine.Pin(1))
uart0.init(bits=8, parity=None, stop=1, timeout=0)

# initialize uart1 to receive gps messages at 4800 baud
uart1 = machine.UART(1, baudrate=4800, tx=machine.Pin(4), rx=machine.Pin(5))
uart1.init(bits=8, parity=None, stop=1, timeout=0)

idle_per = 100

nearest_ships = {}
def update_nearest(ais_data):
    if not 'dist' in ais_data: # if target distance can be is calculated (by alarm compute)
        return
    dist = ais_data['dist']
    if dist >= 10: # dont care about ships further than 10 miles
        return

    mmsi = ais_data['mmsi'] # only keep track of 5 nearest ships for LED flashing calculation
    if not mmsi in nearest_ships and len(nearest_ships) >= 5:
        furthest = 0, None # nearest ships list full, compute farthest ship in nearest ships list
        for ship in nearest_ships:
            furthest = max(furthest[0], nearest_ships[ship][0]), ship
        if dist > furthest[0]:
            return # further than furthest near ship, abort
        del nearest_ships[furthest[1]]
    # update nearest ship list
    nearest_ships[mmsi] = dist, t / 1000

async def iteration():
    gps_data = None
    gps_time = time.ticks_ms()
    ships_led_time = 0
    button_toggle_times = {}
    for button in buttons:
        button_toggle_times[button] = time.ticks_ms()

    while True:
        t = time.ticks_ms()
        # receive ais data
        while True:
            ais_line = non_blocking_readline(uart0)
            if not ais_line:
                break
            await wireless.write_nmea(ais_line)
            try:
                ais_data, nmeas = decode_ais(ais_line)
                print('decoded', ais_data)
            except Exception as e:
                import traceback
                print(traceback.format_exc())
                print('failed decoding ais data', ais_line, e)
                ais_data = False
            if ais_data:
                leds.on_timeout('ais')
                alarm.compute(gps_data, ais_data)
                update_nearest(ais_data)
                await web.ais_data(ais_data, nmeas)

        # receive gps data
        while True:
            gps_line = non_blocking_readline(uart1)
            if not gps_line:
                break
            await wireless.write_nmea(gps_line)
            gps_data = decode_gps(gps_line)
            if gps_data:
                leds.on_timeout('gps', 10)
                gps_time = time.ticks_ms()
                web.gps_data(gps_line)
                alarm.anchor(gps_data)

        # if no gps fix in 30 seconds, alarm!
        if t - gps_time > 30000:
            alarm.alarm(3)

        # flash ships led based on closest ship
        # once per second for 1 mile,  once every 10 seconds if 10 miles
        if t > ships_led_time:
            mindist = 10
            for mmsi in list(nearest_ships):
                dist, shipt = nearest_ships[mmsi]
                if t - shipt > 600:  # timeout nearest ships after 10 minutes
                    del nearest_ships[mmsi] # remove ship
                else:
                    mindist = min(mindist, dist) # find nearest of nearest ships
            if mindist < 10:
                leds.on_timeout('ships') # flash ships LED
                # recompute flash period based on how far the nearest ship is
                ships_led_time = t+mindist*1000 # in milliseconds

        # check buttons to toggle functions
        for name, pin in buttons.items():
            if not pin.value():
                if t-button_toggle_times[name] > 1:
                    value = alarm.config[name]
                    alarm.config[name] = not value
                    button_toggle_times[name] = t
                    leds.value(name, not value)

                    if name == 'anchor':
                        alarm.anchor_pos = gps_data
                    elif name == 'ap':
                        wireless.reset()
                        
        # turn off leds that timed out
        leds.timeout(t)

        # feed the watchdog
        wdt.feed()
        
        # sleep for remainder of second
        sleep_ms = max(1000-time.ticks_ms()+t, 0)
        global idle_per
        idle_per = (sleep_ms/10)*.01 + idle_per*.99
        await asyncio.sleep_ms(sleep_ms)

wdt = machine.WDT(timeout=8000)  # enable it with a timeout of 8s

async def report_statistics():
    while True:
        t0 = time.ticks_ms()
        F = gc.mem_free()
        A = gc.mem_alloc()
        print('mem stat', F, A)
        s = os.statvfs('/')
        t1 = time.ticks_ms()
        print(f"Free storage: {s[0]*s[3]/1024} KB", t1-t0)

        print('iteration idle %', idle_per)
        print('start', starttime/1000, 'run time ', (t1-starttime)/1000)

        micropython.mem_info()
        await asyncio.sleep(60)

leds.value('pwr', True)

print('create tasks')

# create tasks
loop = asyncio.get_event_loop()
loop.create_task(iteration())
loop.create_task(report_statistics())
loop.create_task(wireless.serve_nmea())
loop.create_task(wireless.maintain_connection())
loop.create_task(web.serve())

print('run main loop')
loop.run_forever()

print('finished main loop??')
machine.reset()

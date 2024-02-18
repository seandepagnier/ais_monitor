#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import time, math
from machine import Pin, UART
import machine
import board

from decode_ais import decode_ais
from decode_gps import decode_gps
from alarm import compute_alarm
import wifi

# table for the various leds
led_indicies = {'pwr': 6,
                'ais': 7,
                'gps': 8,
                'ships': 9,
                'ownship': 10,
                'mute': 11}

def led_value(name, v):
    led_pins[led_indicies[name]].value(v)


led_pins = {}
for pin, i in led_pins.items():
    led_pins[pin] = Pin(pin, Pin.OUT)
    led_pins[pin].low()

led = Pin("LED", Pin.OUT)
led.on()

led_value('pwr', True)

led_timeouts = {}
def led_on_timeout(name, t=200):
    global led_timeouts
    led_timeouts[name] = time.ticks_ms()+t
    led_value(name, True)

# this pin is used for a button that mutes the alarm
mute_button = Pin(12, Pin.PULL_UP)

# initialize uart0 to receive gps data at 4800 baud
uart0 = UART(0, baudrate=4800, tx=Pin(0), rx=Pin(1))
uart0.init(bits=8, parity=None, stop=1, timeout=0, invert=UART.INV_TX | UART.INV_RX)

# initialize uart1 to receive ais messages at 38400 baud
uart1 = UART(1, baudrate=38400, tx=Pin(4), rx=Pin(5))
uart1.init(bits=8, parity=None, stop=1, timeout=0, invert=UART.INV_TX | UART.INV_RX)

gps_data = None
ships = {}
ships_led_time = 0

uart0_buffer = bytearray()
uart1_buffer = bytearray()

while True:
    t = time.ticks_ms()
    # receive ais data
    ais_line = wifi.non_blocking_readline(uart1, uart1buffer)
    if ais_line:
        ais_data = decode_ais(ais_line)
        if ais_data:
            ships[ais_data['mmsi']] = ais_data
            led_on_timeout('ais')
            compute_alarm(ais_data)
        wifi.write(ais_line)

    # receive gps data
    gps_line = wifi.non_blocking_readline(uart0, uart0buffer)
    if gps_line:
        gps_data = decode_gps(gps_line)
        led_on('gps', gps_data)
        wifi.write(gps_line)

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
            led_on_timeout('ships')
        ships_led_time = t+mindist

    # check mute button to toggle mute function
    if not mute_button.value():
        if t-mute_toggle_time > 1:
            muted = not muted
            mute_toggle_time = t
        led_on('mute', muted)

    # turn off leds that timed out
    for name, t0 in led_timeouts.items():
        if t > t0:
            led_value(name, False)
        
    # poll wifi for remainder of second
    timeout = max(1-time.ticks_ms()+t, 0)
    wifi.poll(0)

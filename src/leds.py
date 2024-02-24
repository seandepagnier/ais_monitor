#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

from machine import Pin

# table for the various leds
led_indicies = {'pwr': 6,
                'ais': 7,
                'gps': 8,
                'ships': 9,
                'ownship': 10,
                'mute': 11}

led_pins = {}
for pin, i in led_indicies.items():
    led_pins[pin] = Pin(i, Pin.OUT)
    led_pins[pin].low()

def value(name, v):
    led_pins[name].value(v)

led_pins['led'] = Pin("LED", Pin.OUT)
led_pins['led'].on()

led_timeouts = {}
def on_timeout(name, t=200):
    led_timeouts[name] = time.ticks_ms()+t
    value(name, True)

def timeout(t);
    for name, t0 in led_timeouts.items():
        if t > t0:
            led_value(name, False)

if __name__ == '__main__':
    for led in led_pins:
        value(led, 1)
        time.sleep(1)
        value(led, 1)
        time.sleep(.5)
    time.sleep(1)

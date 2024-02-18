#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import math, time

# play a sound out gpio pin speaker for alarms
audio = None
decoder = None

try:
    from audiocore import WaveFile
    from audiopwmio import PWMAudioOut as AudioOut
    audio = AudioOut(board.GP14)
    from audiomp3 import MP3Decoder
    from audiopwmio import PWMAudioOut as AudioOut
    decoder = MP3Decoder(mp3_file)
except Exception as e:
    print('failed to initialize audio', e)
    #mono 22khz 16bit, or mp3 mono 16khz 32kbit

muted = False

def play_sound(filename):
    if muted:
        return

    if not audio:
        return

    with open(filename, 'rb') as wave_file:
        wave = WaveFile(wave_file)
        audio.play(wave)
        while audio.playing:
            pass

def play_mp3(filename):
    if muted:
        return

    if not decoder:
        return

    decoder.file = open(filename, 'rb')
    audio.play(decoder)
    while audio.playing:
        pass


def alarm(index):
    print("ALARM", index)
    if index == 1:
        play_mp3('alarm1.mp3')
    else:
        play_mp3('alarm2.mp3')

#helper trigonomotry functions
def sind(angle):
    return math.sin(math.radians(angle))

def cosd(angle):
    return math.cos(math.radians(angle))

def hypot(x, y):
    return math.sqrt(x*x + y*y)

def resolv(angle):
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

# convert latitude and longitudes into relative 2d coordinates
# this is slightly inaccurate assuming spherical earth model
# but using spherical coordinates (or elliptical earth coordinates)
# is much more complicated and slower, and this is sufficient for useful alarms
def simple_xy(lat1, lon1, lat2, lon2):
    x = cosd(lat1)*resolv(lon1-lon2) * 60
    y = (lat1-lat2)*60 # 60 nautical miles per degree
    return x, y

# from gps data for boat, and ais position data, determine if a collision is imminent
# if so, sound an alarm
def compute_alarm(gps_data, ais_data):
    if not gps_data:
        return

    # now compute cpa and tcpa
    sog = gps_data['sog']
    cog = gps_data['cog']
    asog = ais_data['sog']
    acog = ais_data['cog'] + ais_data['rot']/60*5

    # x and y in relative distance in nautical miles to target
    x, y = simple_xy(gps_data['latitude'], gps_data['longitude'],
                     ais_data['latitude'], ais_data['longitude'])

    dist = hypot(x, y)
    ais_data['dist'] = dist
    if dist < 1: # target is < 1 mile away, make alarm
        alarm(1)

    if dist > 10: # more than 10 miles, no alarm
        return

    # velocity vectors in x, y
    bvx, bvy = sog*sind(cog), sog*cosd(cog)
    avx, avy = asog*sind(acog), asog*cosd(acog)

    # relative velocity of ais target
    vx, vy = avx - bvx, avy - bvy

    # the formula for time of closest approach is when the
    # derivative of the distance with respect to time is zero
    # d = (t*vx+x)^2 + (t*vy+y)^2
    # d = t^2*vx^2 + 2*t*vx*x + x^2 + t^2*vy^2 + 2*t*vy*y + y^2
    # dd/dt = 2*t*vx^2 + 2*vx*x + 2*t*vy^2 + 2*vy*y
    v2 = (vx*vx + vy*vy)
    if v2 < 1e-4: # tracks are nearly parallel courses
        t = 0
    else:
        t = (vx*x + vy*y)/v2

    # distance at point of closest approach
    d = hypot(t*vx - x, t*vy - y)
    
    # time is in hours, convert to seconds
    t *= 3600

    if t < -30:  # tcpa is more than 30 seconds in past, no alarm
        return

    if t > 600: # tcpa is more than 5 minutes in future , no alarm
        return

    if d > 3: # cpa is more than 3 miles away, no alarm
        return
    
    # conditions allow for alarm
    alarm(2)



def ticks_ms():
    try:
        return time.ticks_ms()
    except:
        return int(time.time()*1000)

# for testing
if __name__ == '__main__':
    gps_data = {'latitude': 45, 'longitude': -70, 'sog': 5, 'cog': 90}
    ais_data = {'latitude': 45, 'longitude': -70.1, 'sog': 5.1, 'cog': 90, 'rot': 0}
    
    ticks = ticks_ms()
    compute_alarm(gps_data, ais_data)
    print('took', ticks_ms() - ticks, 'ms')

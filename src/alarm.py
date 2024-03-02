#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import math, time

from sound import play_mp3

config = {'proximity_dist': 1,
          'tcpa_time': 10,
          'tcpa_dist': 3,
          'muted': False}

# 1 = target within 1 mile
# 2 = potential target approaching
# 3 = gps failure
alarmtime = time.ticks_ms()
def alarm(index):
    # sound alarm at most every 10 seconds
    t = time.ticks_ms()
    global alarmtime
    if t - alarmtime < 10*1000:
        return
    alarmtime = t
    
    print("ALARM", index)
    if config['muted']:
        return
    
    if index == 1:
        play_mp3('slow.mp3')
    else:
        play_mp3('happy.mp3')

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
def compute(gps_data, ais_data):
    if not gps_data or not 'sog' in ais_data:
        return

    # now compute cpa and tcpa
    sog = gps_data['sog']
    cog = gps_data['cog']
    asog = ais_data['sog']
    acog = ais_data['cog']
    if 'rot' in ais_data:
        acog += ais_data['rot']/60*5

    # x and y in relative distance in nautical miles to target
    x, y = simple_xy(gps_data['lat'], gps_data['lon'],
                     ais_data['lat'], ais_data['lon'])

    dist = hypot(x, y)
    ais_data['dist'] = dist
    if dist < config['proximity_dist']: # target is < 1 mile away, make alarm
        alarm(1)

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

    # closest point of apprach distance in nautical miles
    d = hypot(t*vx - x, t*vy - y)
    
    # time till closest point of approach is in hours, convert to seconds
    t *= 3600

    if t < -30:  # tcpa is more than 30 seconds in past, no alarm
        return

    if t > 60*config['tcpa_time']: # tcpa is more than 10 minutes in future, no alarm
        return

    if d > config['tcpa_dist']: # cpa is more than 3 miles away, no alarm
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
    
    compute_alarm(gps_data, ais_data)

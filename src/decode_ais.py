#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import time
from nmea import check_nmea_cksum

# see: https://gpsd.gitlab.io/gpsd/AIVDM.html

def getticks():
    try:
        return time.ticks_ms()
    except:
        return time.monotonic()/1000

ais_packets = {}
def decode_ais(line):
    if line[3:6] != 'VDM':
        return False
    if not check_nmea_cksum(line):
        return False
    
    try:
        data = line[7:len(line)-3].split(',')
        fragcount = int(data[0])
        fragindex = int(data[1])
        channel = data[3]
        payload = data[4]
        pad = data[5]
    except Exception as e:
        print('failed to decode', line, e)        

    # generally now i == pad - 5
    if not channel in ais_packets:
        ais_packets[channel] = ([], [])

    data = []
    for byte in payload:
        d = ord(byte) - 48
        if d > 40:
            d -= 8
        for b in range(5,-1,-1):
            if (1<<b) & d:
                data.append(1)
            else:
                data.append(0)

    pdata, nmeas = ais_packets[channel]
    pdata += data
    nmeas.append(line)

    if fragindex == fragcount:
        data, nmeas = ais_packets[channel]
        result = decode_ais_data(data)
        result['channel'] = channel
        ais_packets[channel] = ([], [])
        return result, nmeas
    return False

def sign(x):
    return 1 if x >= 0 else -1

def ais_n(bits, signed=False):
    negative = False
    if signed:
        if bits[0]:
            negative = True
            bits = list(map(lambda x : 0 if x else 1, bits))
        bits = bits[1:]
            
    result = 0
    count = len(bits)
    for i in range(count):
        if bits[i]:
            result |= (1<<(count-i-1))
    if negative:
        result = -(result + 1)

    return result

def ais_t(bits):
    result = ''
    for i in range(0, bits, 6):
        d = ais_n(bits[i:i+6])
        if d == 0:
            break
        if d <= 31:
            d += 64
        result += '%c' % d
    return result;

def ais_rot(bits):
    rot = ais_n(bits, True)
    return sign(rot) * (rot / 4.733)**2

def ais_sog(bits):
    sog = ais_n(bits)
    if sog == 1023:
        return None
    return sog/10.0

def ais_cog(bits):
    cog = ais_n(bits)
    if cog == 3600:
        return None
    return cog / 10.0

def ais_hdg(bits):
    hdg = ais_n(bits)
    if hdg == 511:
        return None
    return hdg

def ais_ll(bits):
    return round(ais_n(bits, True) / 600000.0, 8)

def ais_ts(bits):
    ts = ais_n(bits)
    if ts >= 60:
        ts = None
    return getticks(), ts


def decode_ais_data(data):
    # first byte is message type

    message_type = ais_n(data[0:6]);
    d = {'message_type': message_type,
         'mmsi': ais_n(data[8:38]),
         'ticks_ms': getticks()}
    #print('message_type', d['message_type'])
    if message_type in [1,2,3]:
        d.update({#'status': ais_e(data[38:42]),
                     'rot': ais_rot(data[42:50]),
                     'sog': ais_sog(data[50:60]),
                     #'pos_acc': ais_n(data[60:61]),
                     'lon': ais_ll(data[61:89]),
                     'lat':  ais_ll(data[89:116]),
                     'cog': ais_cog(data[116:128]),
                     #'hdg' = ais_hdg(data[128:137]),
                     #'ts': ais_ts(data[137:143])
        })
    elif message_type in [18, 19]:
        d.update({'sog': ais_sog(data[46:56]),
                  #'pos_acc': ais_n(data[56:57]),
                  'lon': ais_ll(data[57:85]),
                  'lat':  ais_ll(data[85:112]),
                  'cog': ais_cog(data[112:124]),
                  #'hdg' = ais_hdg(data[124:133]),
                  #'ts': ais_ts(data[133:139])
        })
        
    return d

def test1():
    from machine import UART, Pin
    from non_blocking_readline import non_blocking_readline
    uart0 = UART(0, baudrate=38400, tx=Pin(0), rx=Pin(1))
    uart0.init(bits=8, parity=None, stop=1, timeout=0)

    while True:
        line = non_blocking_readline(uart0)
        if line:
            print(line.strip())
            t0 = time.ticks_ms()
            result = decode_ais(line)
            t1 = time.ticks_ms()
            print(result)
            print(t1-t0)
        else:
            time.sleep(1)

def test2():
    packets = ['!AIVDM,1,1,,B,13MARih000wbAbJP0kr23aSV0<0g,0*73',
               '!AIVDM,1,1,,A,13P>Hq0000wbF:pP0jIEdkNH0l0O,0*46',
               '!AIVDM,1,1,,A,13P>Hq0000wbF:lP0jI5dkNH0d0N,0*23',
               '!AIVDM,1,1,,B,33P;FBE000wbHI4P0he=Da?>0000,0*6B',
               '!AIVDM,1,1,,A,13P>Hq0000wbF9rP0jHUdkNv0l0O,0*68',
               '!AIVDM,1,1,,B,39NWtpm000wb=GBP19oqt9qn0Dtr,0*24',
               '!AIVDM,1,1,,B,13MARih000wbAb8P0kpj3aRv06K8,0*54',
               '!AIVDM,1,1,,A,33OhGr1001Ob;SvP1vKFoC@d0De:,0*3E',
               '!AIVDM,1,1,,B,13MARih000wbAatP0kkj3aRH06J`,0*67',
               '!AIVDM,1,1,,B,13P>Hq0000wbF:8P0jFEdkN20l0O,0*78']

    packets = ['!AIVDM,1,1,,A,B52e9Eh00>`aAVUGfPWQ3wgQnDlb,0*4E']
    ticks = getticks()
    for p in packets:
        print(decode_ais(p))

    print('took', getticks() - ticks, 'ms')

#test2()

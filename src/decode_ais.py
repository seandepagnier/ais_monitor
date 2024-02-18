#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import time

from nmea import check_nmea_cksum

ais_packets = {}

def decode_ais(line):
    if not check_nmea_cksum(line):
        return False
    
    if line[3:6] != 'VDM':
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
        ais_packets[channel] = []

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

    ais_packets[channel] += data

    if fragindex == fragcount:
        result = decode_ais_data(channel, ais_packets[channel])
        ais_packets[channel] = []
        return result
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

def decode_ais_data(channel, data):
    # first byte is message type
    message_type = ais_n(data[0:6])
    if message_type not in [1,2,3,18]:
        pass #return
    
    mmsi = ais_n(data[8:38])
    #status = ais_e(data[38:42])

    status = ais_n(data[38:42])

    rot_imm = ais_n(data[42:50], True)
    rate_of_turn = sign(rot_imm) * (rot_imm / 4.733)**2

    sog_imm = ais_n(data[50:60])
    if sog_imm == 1023:
        speed_over_ground = None
    else:
        speed_over_ground = sog_imm/10.0

    pos_acc = ais_n(data[60:61])

    lon_imm = ais_n(data[61:89], True)
    longitude = lon_imm / 600000.0
                              
    lat_imm = ais_n(data[89:116], True)
    latitude = lat_imm / 600000.0

    cog_imm = ais_n(data[116:128])
    if cog_imm == 3600:
        course_over_ground = None
    else:
        course_over_ground = cog_imm / 10.0

    true_hdg_imm = ais_n(data[128:137])
    if true_hdg_imm == 511:
        true_heading = None
    else:
        true_heading = true_hdg_imm

    timestamp_s = ais_n(data[137:143])
    if timestamp_s >= 60:
        timestamp_s = None

    timestamp_s = ais_n(data[137:143])

    return {'mmsi': mmsi,
            'rot': rate_of_turn,
            'sog': speed_over_ground,
            'cog': course_over_ground,
            'lon': longitude,
            'lat': latitude,
            'ts': (time.time(), timestamp_s)}

# test packets
if __name__ == '__main__':
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
    ticks = time.ticks_ms()
    for p in packets:
        print(decode_ais(p))

    print('took', time.ticks_ms() - ticks, 'ms')

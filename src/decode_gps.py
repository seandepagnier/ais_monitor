#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

from nmea import check_nmea_cksum

def decode_gps(line):
    def degrees_minutes_to_decimal(n):
        n/=100
        degrees = int(n)
        minutes = n - degrees
        return degrees + minutes*10/6

    if not check_nmea_cksum(line):
        return False

    if line[3:6] != 'RMC':
        return False

    try:
        data = line[7:len(line)-3].split(',')
        if data[1] == 'V':
            return False
        gps = {}

        lat = degrees_minutes_to_decimal(float(data[2]))
        if data[3] == 'S':
            lat = -lat

        lon = degrees_minutes_to_decimal(float(data[4]))
        if data[5] == 'W':
            lon = -lon

        speed = float(data[6]) if data[6] else 0
        gps = {'sog': speed, 'lat': lat, 'lon': lon}
        if data[7]:
            gps['cog'] = float(data[7])

        if data[9]:
            decl = float(data[9])
            if data[10] == 'W':
                decl = -decl
            
    except Exception as e:
        print('failed to parse gps', line, e)
        return False

    return gps

# test packets
if __name__ == '__main__':
    packets = ['$GPRMC,210230,A,3855.4487,N,09446.0071,W,0.0,076.2,130495,003.8,E*69']
    for p in packets:
        print(decode_gps(p))

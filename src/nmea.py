#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

# nmea uses a simple xor checksum
def nmea_cksum(msg):
    value = 0
    for c in msg: # skip over the $ at the begining of the sentence
        value ^= ord(c)
    return value & 255

def check_nmea_cksum(line):
    cksplit = line.split('*')
    try:
        computed = nmea_cksum(cksplit[0][1:])
        lineck = int(cksplit[1], 16)
        if computed == lineck:
            return True
        print('chekcsum faild', computed, lineck)
        return False
    except Exception as e:
        print('failed checksum exception', e)
        return False

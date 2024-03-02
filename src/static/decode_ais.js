/*
#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  
*/

// see: https://gpsd.gitlab.io/gpsd/AIVDM.html

ais_packets = {};

function getCurrentTime() {
    const now = new Date();
    const hour = now.getHours().toString().padStart(2, '0');
    const minute = now.getMinutes().toString().padStart(2, '0');
    const second = now.getSeconds().toString().padStart(2, '0');
    return `${hour}:${minute}:${second}`;
}

function convertHoursToHMS(hours) {
    var h = Math.floor(hours);
    var m = Math.floor((hours - h) * 60);
    var s = Math.floor(((hours - h) * 60 - m) * 60);

    return h + ":" + (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
}

function nmea_cksum(msg) {
    value = 0;
    for(var i=0; i<msg.length; i++) // skip over the $ at the begining of the sentence
        value ^= msg.charCodeAt(i);
    return value & 255;
}

function check_nmea_cksum(line) {
    try {
        cksplit = line.split('*');
        computed = nmea_cksum(cksplit[0].substring(1));
    lineck = Number('0x' + cksplit[1]);
        return computed == lineck;
    } catch(e) {
    }
    return false;
}

function decode_gps(line) {
    function degrees_minutes_to_decimal(n) {
        n/=100;
        let degrees = Math.round(n);
        let minutes = n - degrees;
        return degrees + minutes*10/6;
    }

    if(line.substr(3,6) != 'RMC')
        return false;

    if(!check_nmea_cksum(line))
        return false;

    try {
        let data = line.substr(7, line.length-3).split(',');
        if(data[1] == 'V')
            return false;

        let lat = degrees_minutes_to_decimal(parseFloat(data[2]));
        if(data[3] == 'S')
            lat = -lat;

        let lon = degrees_minutes_to_decimal(parseFloat(data[4]));
        if(data[5] == 'W')
            lon = -lon;

        let speed = data[6] ? parseFloat(data[6]) : 0;
        var gps = {'sog': speed, 'lat': lat, 'lon': lon, 'timestamp': getCurrentTime()};

        if(data[7])
            gps['cog'] = parseFloat(data[7]);

        if(data[9]) {
            let decl = parseFloat(data[9]);
            if(data[10] == 'W')
                decl = -decl;
        }

    } catch(err) {
        print('failed to parse gps', line, err)
        return false
    }    
    return gps
}

function decode_ais(line) {
    if(line.substring(3, 6) != 'VDM')
        return false;

    if(!check_nmea_cksum(line))
        return false;
    
    try {
        data = line.substring(7, line.length-3).split(',');
        fragcount = Number(data[0]);
        fragindex = Number(data[1]);
        channel = data[3];
        payload = data[4];
        pad = data[5];
    } catch(err) {
        // failed to decode
        return false;
    }

    // generally now i == pad - 5
    if(!(channel in ais_packets))
        ais_packets[channel] = []

    data = [];
    for(var i=0; i < payload.length; i++) {
        d = payload.charCodeAt(i) - 48
        if(d > 40)
            d -= 8;
        for(var b=5; b>=0; b--)
            if((1<<b) & d)
                data.push(1);
            else
                data.push(0);
    }

    pdata = ais_packets[channel];
    pdata.push(...data);

    if(fragindex == fragcount) {
        data = ais_packets[channel];
        result = decode_ais_data(data);
        result['channel'] = channel;
        ais_packets[channel] = [];
        return result
    }
    return false;
}

function ais_n(bits, signed=false) {
    var negative = false;
    if (signed) {
        if (bits[0]) {
            negative = true;
            negbits = [];
            for(bit of bits)
                negbits.push(bit ? 0 : 1);
            bits = negbits;
        }
        bits = bits.slice(1);
    }
            
    var result = 0;
    var count = bits.length;
    for(let i=0; i<count; i++)
        if(bits[i])
            result |= (1<<(count-i-1));

    if(negative) // 2's compliment
        result = -(result + 1);

    return result;
}

function ais_t(bits) {
    result = '';
    for(let i=0; i<bits.length; i+=6) {
        d = ais_n(bits.slice(i, i+6));
        if( d == 0 )
            break;
        if( d <= 31)
            d += 64
        result += String.fromCharCode(d);
    }
    return result;
}

function ais_status(bits) {
    switch(ais_n(bits)) {
    case 0: return 'Under way using engine';
    case 1: return 'At anchor';
    case 2: return 'Not under command';
    case 3: return 'Restricted manoeuverability';
    case 4: return 'Constrained by her draught';
    case 5: return 'Moored';
    case 6: return 'Aground';
    case 7: return 'Engaged in Fishing';
    case 8: return 'Under way sailing';
    case 9: return 'Reserved for future amendment of Navigational Status for HSC';
    case 10: return 'Reserved for future amendment of Navigational Status for WIG';
    case 11: return 'Power-driven vessel towing astern (regional use)';
    case 12: return 'Power-driven vessel pushing ahead or towing alongside (regional use).';
    case 13: return 'Reserved for future use';
    case 14: return 'AIS-SART is active';
    }
    
    return 'Undefined';
}

function ais_rot(bits) {
    let rot = ais_n(bits, true);
    return Math.sign(rot) * (rot / 4.733)**2;
}

function ais_sog(bits) {
    let sog = ais_n(bits);
    if(sog == 1023)
        return null;
    return sog/10.0;
}

function ais_cog(bits) {
    let cog = ais_n(bits);
    if(cog == 3600)
        return null;
    return cog / 10.0;
}

function ais_hdg(bits) {
    let hdg = ais_n(bits);
    if(hdg == 511)
        return null;
    return hdg;
}

function ais_ll(bits) {
    return ais_n(bits, true) / 600000.0;
}

function ais_ts(bits) {
    let ts = ais_n(bits);
    if(ts >= 60)
        ts = null;
    return ts;
}

function ais_e(bits) {
    type = ais_n(bits);
    if(type == 0)                       return 'N/A';
    if(type >= 20 && type <= 29)        return 'WIG';
    switch(type) {
    case 30: return 'Fishing';
    case 31: return 'Towing';
    case 32: return 'Towing: length exceeds 200m or breadth exceeds 25m';
    case 33: return 'Dredging or underwater ops';
    case 34: return 'Diving ops';
    case 35: return 'Military ops';
    case 36: return 'Sailing';
    case 37: return 'Pleasure Craft';
    }
    if(type >= 40 && type <= 49)        return 'High speed craft';
    switch(type) {
    case 30: return 'Fishing';
    case 31: return 'Towing';
    case 32: return 'Towing: length exceeds 200m or breadth exceeds 25m';
    case 33: return 'Dredging or underwater ops';
    case 34: return 'Diving ops';
    case 35: return 'Military ops';
    case 36: return 'Sailing';
    case 37: return 'Pleasure Craft';
    }
    if(type >= 60 && type <= 69)        return 'Passenger';
    if(type >= 70 && type <= 79)        return 'Cargo';
    if(type >= 80 && type <= 89)        return 'Tanker';
    if(type >= 90 && type <= 99)        return 'Other';

    return 'Unknown';
}
    
function decode_ais_data(data) {
    // first byte is message type
    function s(off, len) {
        return data.slice(off, off+len);
    }

    let message_type = ais_n(s(0, 6));

    if(message_type in [1,2,3]) {
        d = {'status': ais_status(s(38,4)),
            'rot': ais_rot(s(42, 8)),
            'sog': ais_sog(s(50, 10)),
            //'pos_acc': ais_n(data[60:61)),
            'lon': ais_ll(s(61, 28)),
            'lat':  ais_ll(s(89, 27)),
            'cog': ais_cog(s(116, 12)),
            //'hdg' = ais_hdg(data[128:137)),
        };
    } else if(message_type == 5) {
        d = {'callsign':   ais_t(s(70, 42)),
             'name': ais_t(s(112, 120)),
             'ship type':   ais_e(s(232, 8)),
             'dimensions':  [ais_n(s(240, 9)), ais_n(s(249, 9)),
                             ais_n(s(258, 6)), ais_n(s(264, 6))],
             'draught':     ais_n(s(294, 8)),
             'destination': ais_t(s(302, 120))};
    } else if(message_type == 18) {
        d = {'sog': ais_sog(s(46, 10)),
             'lon': ais_ll(s(57, 28)),
             'lat': ais_ll(s(85, 27)),
             'cog': ais_cog(s(112, 12)),
             'hdg': ais_hdg(s(124, 9))
            };
    } else if(message_type == 19) {
        d = {'sog': ais_sog(s(46, 10)),
             'lon': ais_ll(s(57, 28)),
             'lat': ais_ll(s(85, 27)),
             'cog': ais_cog(s(112, 12)),
             'hdg': ais_hdg(s(124, 9)),
             'name': ais_t(s(143, 120)),
             'ship type':   ais_e(s(263, 8)),
             'dimensions': [ais_n(s(271, 9)), ais_n(s(280, 9)),
                            ais_n(s(289, 6)), ais_n(s(295, 6))]
            };
    } else if(message_type == 24) {
        let part_num = ais_n(s(38,2));
        if(part_num == 0) {
            d = {'name': ais_t(s(40, 120))};
        } else if(part_num == 1) {
            d = {'ship type': ais_e(s(40, 8)),
                 'callsign': ais_t(s(90, 42)),
                 'dimensions': [ais_n(s(132, 9)), ais_n(s(141, 9)),
                                ais_n(s(150, 6)), ais_n(s(156, 6))]
                };
        }
    } else
        return false;

    data = {'message_type': message_type,
            'mmsi': ais_n(s(8, 30)),
            'timestamp': getCurrentTime()};
    return {...data, ...d};
}

function simple_xy(lat1, lon1, lat2, lon2) {
    let x = cosd(lat1)*resolv(lon1-lon2) * 60;
    let y = (lat1-lat2)*60; // 60 nautical miles per degree
    return x, y;
}

// compute distance, cpa and tcpa, and put into ais_data
function compute(gps_data, ais_data) {
    function sind(angle) {
        return Math.sin(angle*Math.PI/180);
    }
    function sd(angle) {
        return Math.cos(angle*Math.PI/180);
    }

    if(!gps_data || !('sog' in ais_data))
        return
    let sog = gps_data['sog'];
    let cog = gps_data['cog'];
    let asog = ais_data['sog'];
    let acog = ais_data['cog'];

    xy = simple_xy(gps_data['lat'], gps_data['lon'],
                   ais_data['lat'], ais_data['lon']);

    dist = Math.hypot(...xy);
    ais_data['dist'] = dist;

    // velocity vectors in x, y
    let bv = [sog*sind(cog), sog*cosd(cog)];
    let av = [asog*sind(acog), asog*cosd(acog)];

    // relative velocity of ais target
    let v = [av[0] - bv[0], av[1] - bv[1]];
        
    //the formula for time of closest approach
    let v2 = (v[0]*v[0] + v[1]*v[1]);
    let t = 0;
    if(v2 > 1e-4) // tracks are not nearly parallel courses
        t = (v[0]*xy[0] + v[1]*xy[1])/v2;

    // closest point of apprach distance in nautical miles
    ais_data['cpa'] = Math.hypot(t*v[0] - xy[0], t*v[1] - xy[1]);
    
    // time till closest point of approach is in hours, convert to seconds
    ais_data['tcpa'] = convertHoursToHMS(t);
}

function test() {
    packets = ['!AIVDM,1,1,,B,13MARih000wbAbJP0kr23aSV0<0g,0*73',
               '!AIVDM,1,1,,A,13P>Hq0000wbF:pP0jIEdkNH0l0O,0*46',
               '!AIVDM,1,1,,A,13P>Hq0000wbF:lP0jI5dkNH0d0N,0*23',
               '!AIVDM,1,1,,B,33P;FBE000wbHI4P0he=Da?>0000,0*6B',
               '!AIVDM,1,1,,A,13P>Hq0000wbF9rP0jHUdkNv0l0O,0*68',
               '!AIVDM,1,1,,B,39NWtpm000wb=GBP19oqt9qn0Dtr,0*24',
               '!AIVDM,1,1,,B,13MARih000wbAb8P0kpj3aRv06K8,0*54',
               '!AIVDM,1,1,,A,33OhGr1001Ob;SvP1vKFoC@d0De:,0*3E',
               '!AIVDM,1,1,,B,13MARih000wbAatP0kkj3aRH06J`,0*67',
               '!AIVDM,1,1,,B,13P>Hq0000wbF:8P0jFEdkN20l0O,0*78'];
    packets = ['!AIVDM,1,1,,A,H52e9ElUCBD:0:<00000001H104t,0*08'];
    const start = Date.now();
    for(p of packets) {
        result = decode_ais(p);
        console.log(result);
    }
    const end = Date.now();
    console.log(`Execution time: ${end - start} ms`);
}

test()

/*
#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  
*/

var socket = null;
var ship_table = document.getElementById('ships_table');

function connect_websocket() {
    console.log('try to connect')
    socket = new WebSocket('ws://' + location.host + '/ws');

    socket.addEventListener('message', ev => {
        let line = ev.data;
        if(line.substring(3, 6) == 'VDM')
            ais_message(line);
        else
            gps_message(line);
    });

    socket.addEventListener('close', ev => {
        console.log('<<< closed');

        // try to reconnect
        setTimeout(connect_websocket, 5000);
    });
}

connect_websocket();
ships = {};

var last_gps = null;
function gps_message(data) {
    result = decode_gps(data);
    if(!result)
        return;

    fields=['sog', 'cog', 'lat', 'lon', 'timestamp']
    for(field of fields)
        if(field in result) {
            let div = document.getElementById(field);
            div.innerText = result[field];
        }
    last_gps = result;
}

function ais_message(data) {
    console.log(data);
    let result = decode_ais(data);
    compute(last_gps, result);
    console.log(result);
    if(!result)
        return;

    let mmsi = result['mmsi'];
    let fields = ['channel', 'name', 'callsign', 'type', 'status', 'dist', 'cog', 'sog', 'cpa', 'tcpa', 'timestamp']    
    if(!(mmsi in ships)) {
        let row = ship_table.insertRow(1);
        let c = 0;
        row.insertCell(c++).innerText = mmsi;
        for(field of fields)
            row.insertCell(c++).innerHTML = "<div id='" + field+mmsi+"'></div>";

        ships[mmsi] = result;
    } else {
        for(field of result)
            ships[mmsi][field] = result[field];
    }

    for(field of fields)
        if(field in result) {
            let div = document.getElementById(field+mmsi);
            div.innerText = result[field];
        }
}

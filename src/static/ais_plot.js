/*
#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  
*/


/*============= Creating a canvas ======================*/
var canvas = document.getElementById('canvas');
gl = canvas.getContext('webgl');

// drawing radar rings
var circle_vertices = [];
for(var ang=0; ang<=360; ang+=4) {
    var rang = Math.PI*2*ang/360;
    circle_vertices.push(Math.sin(rang));
    circle_vertices.push(Math.cos(rang));
}

var circle_vertex_buffer = gl.createBuffer ();
gl.bindBuffer(gl.ARRAY_BUFFER, circle_vertex_buffer);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(circle_vertices), gl.STATIC_DRAW);

var vertCode =
    'attribute vec2 position;'+
    'uniform float scale;'+
    'void main(void) { '+
    'gl_Position = vec4(scale*position,0,1);' +
    '}';

var fragCode = 'precision mediump float;'+
    'void main(void) {'+
    'gl_FragColor = vec4(1, 1, 1, 1.);'+
    '}';

function make_program(vert, frag) {
    var vertShader = gl.createShader(gl.VERTEX_SHADER);
    gl.shaderSource(vertShader, vert);
    gl.compileShader(vertShader);

    var fragShader = gl.createShader(gl.FRAGMENT_SHADER);
    gl.shaderSource(fragShader, frag);
    gl.compileShader(fragShader);

    var program = gl.createProgram();
    gl.attachShader(program, vertShader);
    gl.attachShader(program, fragShader);
    gl.linkProgram(program);
    return program;
}

radarringsprogram = make_program(vertCode, fragCode);

function draw_radar_rings() {
    gl.useProgram(radarringsprogram);
    var _position = gl.getAttribLocation(radarringsprogram, "position");
    gl.enableVertexAttribArray(_position);

    var _scale = gl.getUniformLocation(radarringsprogram, "scale");
    gl.bindBuffer(gl.ARRAY_BUFFER, circle_vertex_buffer);
    gl.vertexAttribPointer(_position, 2, gl.FLOAT, false,0,0);

    gl.uniform1f(_scale, 1);
    gl.drawArrays(gl.LINE_LOOP, 0, circle_vertices.length/2);

    gl.uniform1f(_scale, .5);
    gl.drawArrays(gl.LINE_LOOP, 0, circle_vertices.length/2);
}


// Drawing ships
var vertCode =
    'attribute vec2 a_texCoord;' +
    'uniform vec2 u_pos;' +
    'uniform vec2 u_scale;' +
    'uniform mat2 Mmatrix;'+
    'varying vec2 v_texCoord;' +
    'void main() {' +
    '   vec2 coord = a_texCoord*u_scale*vec2(2,2) - u_scale;' +
    '   gl_Position = vec4(u_pos + Mmatrix*coord, 0, 1);' +
    '   v_texCoord = a_texCoord;' +
    '}';

var fragCode =
    'precision mediump float;' +
    'uniform sampler2D u_image;' +
    'varying vec2 v_texCoord;' +
    'void main() {' +
    '   gl_FragColor = texture2D(u_image, v_texCoord).rgba;' +
    '}';

shipprogram = make_program(vertCode, fragCode);


// look up where the vertex data needs to go.
var texcoordLocation = gl.getAttribLocation(shipprogram, "a_texCoord");

// provide texture coordinates for the rectangle.
var texcoordBuffer = gl.createBuffer();
gl.bindBuffer(gl.ARRAY_BUFFER, texcoordBuffer);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    0.0,  0.0, 1.0,  0.0, 0.0,  1.0, 0.0,  1.0, 1.0,  0.0, 1.0,  1.0,
]), gl.STATIC_DRAW);


// lines for closest point of approach
var vertCode =
    'attribute vec2 position;'+
    'void main(void) { '+
    'gl_Position = vec4(position,0,1);' +
    'gl_PointSize = 4.0;' +
    '}';

var predfragCode = 'precision mediump float;'+
    'uniform vec2 resolution;'+
    'uniform vec2 center;'+
    'void main(void) {'+
    'gl_FragColor = vec4(1, 0, .3, 1);'+
    'vec2 uv = vec2(2,2)*gl_FragCoord.xy/resolution - vec2(1,1) - center;'+
    'float uv_mod = mod(sqrt(uv.x*uv.x + uv.y*uv.y)*15.0, 1.0);'+
    'if(uv_mod < 0.7)'+
    '    discard;'+
    '}';

var cpafragCode = 'precision mediump float;'+
    'uniform vec2 resolution;'+
    'uniform vec2 center;'+
    'void main(void) {'+
    'gl_FragColor = vec4(.1, 1, .2, 1);'+
    'vec2 uv = vec2(2,2)*gl_FragCoord.xy/resolution - vec2(1,1) - center;'+
    'float uv_mod = mod(sqrt(uv.x*uv.x + uv.y*uv.y)*25.0, 1.0);'+
    'if(uv_mod < 0.7)'+
    '    discard;'+
    '}';

var cpafragPointCode = 'precision mediump float;'+
    'void main(void) {'+
    'gl_FragColor = vec4(0, 1, .4, 1);'+
    '}';


predprogram = make_program(vertCode, predfragCode);
cpaprogram = make_program(vertCode, cpafragCode);
cpapointprogram = make_program(vertCode, cpafragPointCode);


var pred_vertex_buffer = gl.createBuffer ();


class ship {
    constructor(path, scale) {
        var image = new Image();
        //ship.src = 'http://' + location.host + '/ship.png';
        image.src = path;
        this.scale = scale;
        image.onload = () => {
            // Create a texture.
            var texture = gl.createTexture();
            gl.bindTexture(gl.TEXTURE_2D, texture);
            this.texture = texture;

            // Set the parameters so we can render any size image.
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);

            // Upload the image into the texture.
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        };
    }

    render(x, y, angle) {
        gl.bindTexture(gl.TEXTURE_2D, this.texture);

        // Tell it to use our program (pair of shaders)
        var program = shipprogram;
        gl.useProgram(program);

        var posLocation = gl.getUniformLocation(program, "u_pos");
        gl.uniform2f(posLocation, x, y, angle);

        var _Mmatrix = gl.getUniformLocation(program, "Mmatrix");
        var rad = Math.PI/180*angle;
        var s = Math.sin(rad);
        var c = Math.cos(rad);
        var mo_matrix = [ c, -s, -s, -c ]
        gl.uniformMatrix2fv(_Mmatrix, false, mo_matrix);
            
        // set ship scale;
        var scaleLocation = gl.getUniformLocation(program, "u_scale");
        
        gl.uniform2f(scaleLocation, this.scale[0], this.scale[1]);
    
        gl.enableVertexAttribArray(texcoordLocation);
        gl.bindBuffer(gl.ARRAY_BUFFER, texcoordBuffer);
        gl.vertexAttribPointer(texcoordLocation, 2, gl.FLOAT, false, 0, 0);

        // Draw the rectangle.
        gl.drawArrays(gl.TRIANGLES, 0, 6);

        // drawing prediction
        gl.bindBuffer(gl.ARRAY_BUFFER, pred_vertex_buffer);
        let predvertices = [x, y, x+s*2, y+c*2];
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(predvertices), gl.DYNAMIC_DRAW);
        
        gl.useProgram(predprogram);

        var _resolution = gl.getUniformLocation(predprogram, "resolution");
        gl.uniform2f(_resolution, canvas.width, canvas.height);
        var _center = gl.getUniformLocation(predprogram, "center");
        gl.uniform2f(_center, x, y);
        
        var _position = gl.getAttribLocation(predprogram, "position");
        gl.enableVertexAttribArray(_position);
        gl.vertexAttribPointer(_position, 2, gl.FLOAT, false, 0, 0);
        gl.drawArrays(gl.LINES, 0, 2);
    }
}

cargoship = new ship('ship.png', [1/80., 1/12]);
yacht = new ship('yacht.png', [1/100., 1/20.]);
ownship = new ship('ownship.png', [1/50., 1/16.]);


function cosd(angle) {
    return Math.cos(angle*Math.PI/180);
}

function resolv(angle) {
    while(angle > 180)
        angle -= 360;
    while(angle < -180)
        angle += 360;
    return angle;
}

function simple_xy(lat1, lon1, lat2, lon2) {
    let x = cosd(lat1)*resolv(lon1-lon2) * 60;
    let y = (lat1-lat2)*60; // 60 nautical miles per degree
    return [x, y];
}

var range = document.getElementById('radar_range');

var animate = function(time) {
    setTimeout(animate, 100);

    gl.clearColor(.17, .42, .51, 1);
    gl.viewport(0.0, 0.0, canvas.width, canvas.height);
    gl.clear(gl.COLOR_BUFFER_BIT);

    draw_radar_rings();

    if(!last_gps)
        return

    glat = last_gps['lat'];
    glon = last_gps['lon'];
    gsog = last_gps['sog'];
    gcog = last_gps['cog'];

    ownship.render(0, 0, gcog);

    let scale = range.value * 2;

    Object.entries(ships).forEach(([mmsi,ship]) => {
        let _ship = ship['channel'] == 'B' ? yacht : cargoship;
        let slat = ship['lat'];
        let slon = ship['lon'];
        let cog = ship['cog'];
        let sog = ship['sog'];
        
        let xy = simple_xy(glat, glon, slat, slon);
        
        let x = xy[0] / scale;
        let y = -xy[1] / scale;
        _ship.render(x, y, cog);

        // render cpa
        if('tcpa_h' in ship) {
            let tcpa_h = ship['tcpa_h'];

            let rad = Math.PI/180*gcog;
            let gs = Math.sin(rad);
            let gc = Math.cos(rad);
            let gd = tcpa_h*gsog/scale;
            
            rad = Math.PI/180*cog;
            let s = Math.sin(rad);
            let c = Math.cos(rad);
            let d = tcpa_h*sog/scale;
            let cpavertices = [gs*gd, gc*gd, x+s*d, y+c*d];
            
            gl.bindBuffer(gl.ARRAY_BUFFER, pred_vertex_buffer);
            gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(cpavertices), gl.DYNAMIC_DRAW);
        
            gl.useProgram(cpaprogram);

            var _resolution = gl.getUniformLocation(cpaprogram, "resolution");
            gl.uniform2f(_resolution, canvas.width, canvas.height);
            var _center = gl.getUniformLocation(cpaprogram, "center");
            gl.uniform2f(_center, cpavertices[0], cpavertices[1]);
        
            var _position = gl.getAttribLocation(cpaprogram, "position");
            gl.enableVertexAttribArray(_position);
            gl.vertexAttribPointer(_position, 2, gl.FLOAT, false, 0, 0);
            gl.drawArrays(gl.LINES, 0, 2);

            gl.useProgram(cpapointprogram);

            var _position = gl.getAttribLocation(cpapointprogram, "position");
            gl.enableVertexAttribArray(_position);
            gl.vertexAttribPointer(_position, 2, gl.FLOAT, false, 0, 0);
            gl.drawArrays(gl.POINTS, 0, 2);
        }
    });


    last_gps['cog'] += 2;
}

animate(0);

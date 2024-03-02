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

//========== Defining and storing the geometry ==========

/*
var circle_vertices = [];
for(var ang=0; ang<=360; ang+=9) {
    var rang = Math.PI*2*ang/360;
    circle_vertices.push(Math.sin(rang));
    circle_vertices.push(Math.cos(rang));
}

// Create and store data into vertex buffer
var circle_vertex_buffer = gl.createBuffer ();
gl.bindBuffer(gl.ARRAY_BUFFER, circle_vertex_buffer);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(circle_vertices), gl.STATIC_DRAW);

//=================== SHADERS =================== 

var vertCode = 'attribute vec2 position;'+
    'uniform mat4 Vmatrix;'+
    'uniform mat4 Mmatrix;'+
    'void main(void) { '+//pre-built function
    'gl_Position = Vmatrix*Mmatrix*vec4(position,0,1);' +
    'gl_PointSize = 3.0;'+
    '}';

var fragCode = 'precision mediump float;'+
    'uniform vec3 vColor;'+
    'void main(void) {'+
        'gl_FragColor = vec4(vColor, 1.);'+
    '}';

var vertShader = gl.createShader(gl.VERTEX_SHADER);
gl.shaderSource(vertShader, vertCode);
gl.compileShader(vertShader);

var fragShader = gl.createShader(gl.FRAGMENT_SHADER);
gl.shaderSource(fragShader, fragCode);
gl.compileShader(fragShader);

var shaderprogram = gl.createProgram();
gl.attachShader(shaderprogram, vertShader);
gl.attachShader(shaderprogram, fragShader);
gl.linkProgram(shaderprogram);

//======== Associating attributes to vertex shader =====
var _Vmatrix = gl.getUniformLocation(shaderprogram, "Vmatrix");
var _Mmatrix = gl.getUniformLocation(shaderprogram, "Mmatrix");

var _color = gl.getUniformLocation(shaderprogram, "vColor");

var _position = gl.getAttribLocation(shaderprogram, "position");
gl.enableVertexAttribArray(_position);

gl.useProgram(shaderprogram);

//==================== MATRIX ====================== 

var mo_matrix = [ 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 ];
var view_matrix = [ 1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1 ];

//view_matrix[14] = view_matrix[14]+3;

*/
//=================== Drawing =================== 

let scale = 1;
function scale_matrix(scale) {
    return [ scale,0,0,0, 0,scale,0,0, 0,0,scale,0, 0,0,0,1 ];
}


/* Drawing ships */

var image = new Image();
image.src = 'http://' + location.host + '/ship.png';
image.onload = function() {
    render(image);
};


function render(image) {
var vertCode =
'attribute vec2 a_position;' +
'attribute vec2 a_texCoord;' +
'uniform vec2 u_resolution;' +
'varying vec2 v_texCoord;' +
'void main() {' +
'   vec2 zeroToOne = a_position / u_resolution;' +
'   vec2 zeroToTwo = zeroToOne * 1.0;' +
'   vec2 clipSpace = zeroToTwo - 0.0;' +
'   gl_Position = vec4(clipSpace * vec2(1, -1), 0, 1);' +
'   v_texCoord = a_texCoord;' +
'}'

var fragCode =
'precision mediump float;' +
'uniform sampler2D u_image;' +
'varying vec2 v_texCoord;' +
'void main() {' +
'   gl_FragColor = texture2D(u_image, v_texCoord).rgba;' +
'}'

var vertShader = gl.createShader(gl.VERTEX_SHADER);
gl.shaderSource(vertShader, vertCode);
gl.compileShader(vertShader);

var fragShader = gl.createShader(gl.FRAGMENT_SHADER);
gl.shaderSource(fragShader, fragCode);
gl.compileShader(fragShader);

var program = gl.createProgram();
gl.attachShader(program, vertShader);
gl.attachShader(program, fragShader);
gl.linkProgram(program);

  // look up where the vertex data needs to go.
  var positionLocation = gl.getAttribLocation(program, "a_position");
  var texcoordLocation = gl.getAttribLocation(program, "a_texCoord");

  // Create a buffer to put three 2d clip space points in
  var positionBuffer = gl.createBuffer();

  // Bind it to ARRAY_BUFFER (think of it as ARRAY_BUFFER = positionBuffer)
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
  // Set a rectangle the same size as the image.
  setRectangle(gl, 0, 0, image.width, image.height);

  // provide texture coordinates for the rectangle.
  var texcoordBuffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, texcoordBuffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
      0.0,  0.0,
      1.0,  0.0,
      0.0,  1.0,
      0.0,  1.0,
      1.0,  0.0,
      1.0,  1.0,
  ]), gl.STATIC_DRAW);

  // Create a texture.
  var texture = gl.createTexture();
  gl.bindTexture(gl.TEXTURE_2D, texture);

  // Set the parameters so we can render any size image.
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
  gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);

  // Upload the image into the texture.
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);

  // lookup uniforms
  var resolutionLocation = gl.getUniformLocation(program, "u_resolution");

    //webglUtils.resizeCanvasToDisplaySize(gl.canvas);

  // Tell WebGL how to convert from clip space to pixels
  gl.viewport(0, 0, gl.canvas.width, gl.canvas.height);

  // Clear the canvas
  gl.clearColor(0, 0, 0, 1);
  gl.clear(gl.COLOR_BUFFER_BIT);

  // Tell it to use our program (pair of shaders)
  gl.useProgram(program);

  // Turn on the position attribute
  gl.enableVertexAttribArray(positionLocation);

  // Bind the position buffer.
  gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);

  // Tell the position attribute how to get data out of positionBuffer (ARRAY_BUFFER)
  var size = 2;          // 2 components per iteration
  var type = gl.FLOAT;   // the data is 32bit floats
  var normalize = false; // don't normalize the data
  var stride = 0;        // 0 = move forward size * sizeof(type) each iteration to get the next position
  var offset = 0;        // start at the beginning of the buffer
  gl.vertexAttribPointer(positionLocation, size, type, normalize, stride, offset);

  // Turn on the texcoord attribute
  gl.enableVertexAttribArray(texcoordLocation);

  // bind the texcoord buffer.
  gl.bindBuffer(gl.ARRAY_BUFFER, texcoordBuffer);

  // Tell the texcoord attribute how to get data out of texcoordBuffer (ARRAY_BUFFER)
  var size = 2;          // 2 components per iteration
  var type = gl.FLOAT;   // the data is 32bit floats
  var normalize = false; // don't normalize the data
  var stride = 0;        // 0 = move forward size * sizeof(type) each iteration to get the next position
  var offset = 0;        // start at the beginning of the buffer
  gl.vertexAttribPointer(texcoordLocation, size, type, normalize, stride, offset);

  // set the resolution
  gl.uniform2f(resolutionLocation, gl.canvas.width, gl.canvas.height);

  // Draw the rectangle.
  var primitiveType = gl.TRIANGLES;
  var offset = 0;
  var count = 6;
  gl.drawArrays(primitiveType, offset, count);
}

function setRectangle(gl, x, y, width, height) {
  var x1 = x;
  var x2 = x + width;
  var y1 = y;
  var y2 = y + height;
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
     x1, y1,
     x2, y1,
     x1, y2,
     x1, y2,
     x2, y1,
     x2, y2,
  ]), gl.STATIC_DRAW);
}





var animate = function(time) {

    gl.clearColor(0, 0, 0, 1);
    gl.viewport(0.0, 0.0, canvas.width, canvas.height);
    gl.clear(gl.COLOR_BUFFER_BIT);

    //set model matrix to I4
    view_matrix = scale_matrix(scale);

    gl.uniformMatrix4fv(_Vmatrix, false, view_matrix);

    mo_matrix = scale_matrix(1);
    gl.uniformMatrix4fv(_Mmatrix, false, mo_matrix);

    gl.uniform3f(_color, 1, 1, 1);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, circle_vertex_buffer);
    gl.vertexAttribPointer(_position, 2, gl.FLOAT, false,0,0);
    gl.drawArrays(gl.LINE_LOOP, 0, circle_vertices.length/2);

    mo_matrix = scale_matrix(.5);
    gl.uniformMatrix4fv(_Mmatrix, false, mo_matrix);
    
    gl.bindBuffer(gl.ARRAY_BUFFER, circle_vertex_buffer);
    gl.vertexAttribPointer(_position, 2, gl.FLOAT, false,0,0);
    gl.drawArrays(gl.LINE_LOOP, 0, circle_vertices.length/2);

    window.requestAnimationFrame(animate);
}
//animate(0);

var range = document.getElementById('radar_range');

range.addEventListener('change', () => {
    scale = range.value;
})

#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

import network
import socket
from time import sleep
from machine import UART, Pin

import select

ssid="mars"
password="rmyu030/"

#Connect to WLAN
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

server_connection = False
test=11

clients = []
poller = select.poll()
def poll(timeout):
    global server_connection
    if wlan.isconnected():
        if not server_connection:
            # Open a socket
            ip = wlan.ifconfig()[0]
            print('using ip', ip)

            address = (ip, 1234)
            server_connection = socket.socket()
            server_connection.bind(address)
            server_connection.listen(1)
            poller.register(server_connection, select.POLLIN)
            
            print('server socket', server_connection)
    else:
        if server_connection:
            poller.unregister(server_connection)
            server_connection.close()
            server_connection = False

    events = poller.poll(timeout)
    for event in events:
        conn = event[0]
        flags = event[1]
        if conn == server_connection:
            client = conn.accept()[0]
            client.settimeout(0)
            clients.append(client)
            poller.register(client, select.POLLIN)
            print('accept server_connection', client)
        elif flags & (select.POLLHUP | select.POLLERR):
            if conn in clients:
                print('close server_connection', conn)
                clients.remove(conn)
                poller.unregister(conn)
                conn.close()

def write(line):
    for client in clients:
        try:
            l = client.write(line)
        except Exception as e:
            print("exception writing to client", e, client)
            client.close()
        if l != len(line):
            print("partial write to client", l, len(line))
            client.close()

def non_blocking_readline(uart, line_buffer):
    line = uart.readline()  # Attempt to read a line (non-blocking)
    if line:
        line_buffer.extend(line)
        if line.endswith(b'\n'):  # Check if the line is complete
            complete_line = bytearray(line_buffer)
            line_buffer[:] = bytearray()  # Clear the buffer for the next line
            return complete_line
    return None  # Return None if no complete line was available

                
if __name__ == '__main__':
    uart0 = UART(0, baudrate=4800, tx=Pin(0), rx=Pin(1))
    uart0.init(4800, bits=8, parity=None, stop=1, timeout=0, invert=UART.INV_TX | UART.INV_RX)
    uart0_buffer = bytearray()

    print('entering main loop')
    while True:
        poll(100)
        while True:
            line = non_blocking_readline(uart0, uart0_buffer)
            if not line:
                break
            write(line)

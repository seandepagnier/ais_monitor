#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  


buffers = {}

def non_blocking_readline(uart):
    if not uart in buffers:
        buffers[uart] = bytearray()

    line_buffer = buffers[uart]

    line = uart.readline()  # Attempt to read a line (non-blocking)
    if line:
        line_buffer.extend(line)
        if line.endswith(b'\n'):  # Check if the line is complete
            complete_line = line_buffer
            buffers[uart] = bytearray()  # Clear the buffer for the next line
            return complete_line.decode()
    return None  # Return None if no complete line was available

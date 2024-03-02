#   Copyright (C) 2024 Sean D'Epagnier
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.  

# play a sound out gpio pin speaker for alarms
audio = None
decoder = None

muted=True

# try to load audio core
try:
    import board
    from audiocore import WaveFile
    from audiopwmio import PWMAudioOut as AudioOut
    audio = AudioOut(board.GP14)
    from audiomp3 import MP3Decoder
    mp3_file = 'slow.mp3'
    decoder = MP3Decoder(mp3_file)
except Exception as e:
    print('failed to initialize audio', e)
    #mono 22khz 16bit, or mp3 mono 16khz 32kbit

def play_sound(filename):
    if not audio:
        return

    with open(filename, 'rb') as wave_file:
        wave = WaveFile(wave_file)
        audio.play(wave)
        while audio.playing:
            pass

def play_mp3(filename):
    if muted:
        print('muted, not playing', filename)
        return

    if not decoder:
        return

    print('opening', filename)
    decoder.file = open(filename, 'rb')
    print('playing', filename)
    audio.play(decoder)
    while audio.playing:
        pass
    print('done playing', filename)


# for testing
if __name__ == '__main__':
    play_mp3('slow.mp3')

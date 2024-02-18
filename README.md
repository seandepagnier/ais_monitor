This project is intended to create a simple device that monitors ship traffic and gps location
to sound audible alarms if there is potential for a collision.

It is inspired by the author's experience colliding with a cargo ship while under sail many
miles offshore in deep water.  Despite collision regulations regarding sail vs powered vessels,
commercial ships often do not keep an active watch, and do not set their radar to detect sailboats.

The primary AIS antenna had failed, and the author was very tired from many hours without sleep.
The intention is to create a reliable redundant backup alarm system with an internal 10 hour battery
to ensure an alarm will be heard even in the event of power failure.

The design uses a dAISy receiver coupled with a raspberry pi pico W.  The schematic provides isolated powersupply,
and maintains the battery at a standby level that does not greatly age the battery.   There is an external
speaker.  The nmea streams can be easily accesed via a tcp socket once the pi pico is connected to a wifi network.

free software targeting micropython performs all the calculations and functions and can be easily modified


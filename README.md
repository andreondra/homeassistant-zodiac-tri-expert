# Zodiac Tri Expert for Home Assistant
This repository contains Python module for integrating Zodiac Tri Expert SWGs to the Home Assistant via MQTT.
It supports reading pH and ACL (ORP) setpoint and current values as well as setting output power (or boost mode).

## Connection to the Zodiac
This script communicates with the Zodiac SWG via serial port. You can use either RS485, which is the official
way, or, as I did, you can connect directly to the Microchip PIC microcontroller's USART TX and RX.

RS485 is located below the pH/ACL module cover on the PCB in the middle. Connection points are marked
as A, B, Pos and 0V. RS485 signals go to the A, B. You also need to apply 5V using power adapter
between Pos and 0V points, so the integrated RS485 transmitter powers on. Beware that higher voltage
may screw up the transmitter.

RS485 may not work (I did not find any specific reason why mine didn't, maybe I destroyed it during my previous experiments),
so as an alternative, you may connect directly to the microprocessor behind the display. This process
can certainly screw up your SWG, so I'm not providing more information. Just look at the chip model
inside your device, find the datasheet and TX, RX pins locations on the microprocessor and solder wires.

You need to change controller type in the Zodiac's menu to the `Aqualink Tri`. If you do not see
this entry in the controller menu, this integration will not work. Support for `Jandy` may be
added to this integration, the address change will be needed and pH/ORP values will not be supported
-- however, I do not need it so you are welcome to open a PR.  Or you can use other projects.

## Script usage
At first, install all dependencies. You probably want to use the virtual environment to not mess
with you system packages:
```sh
python3 -m venv venv
source venv/bin/activate
pip3 install pyserial pyaml ha-mqtt-discoverable
```

Then rename `config.example.yaml` to `config.yaml` and set fill in required information. You can
delete optional fields to use default values.

Launch the script with:
```sh
python3 -m zodiac-tri-expert
```

You would probably want to autostart the script on system boot. Example systemd service is provided
in the repository.

## Requirements & Dependencies
Requires at least Python 3.11 and these packages (available from pip):
- pyserial
- pyaml
- ha-mqtt-discoverable

## Contributions
Some stuff is not yet implemeted (terminal interface, error code detection...). If you want to contribute,
just open a PR. Thanks 😀.

## Further discussion and information
A lot of valuable information can be found in the [AquapureD](https://github.com/sfeakes/AquapureD) project issues discussions.

## Acknowledgements
I would like to thank guys around the AquapureD project, the project itself and discussions around it
helped me a lot to gain information about the protocol, connections and more. Also I would like
to thank random people on the pool-related forums for sharing what they know, so we all can build
good stuff.

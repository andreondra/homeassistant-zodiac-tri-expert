# Zodiac Tri Expert control
This repository contains Python module for integrating Zodiac Tri Expert SWGs to the Home Assistant via MQTT.

## Usage
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

## Acknowledgements
I would like to thank guys around the AquapureD project, the project itself and discussions around it
helped me a lot to gain information about the protocol, connections and more. Also I would like
to thank random people on the pool-related forums for sharing what they know, so we all can build
good stuff.

from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo, Sensor, SensorInfo
import yaml
from pathlib import Path
import logging
from time import sleep

from .constants  import *
from .exceptions import *
from .aqualink   import Aqualink

_LOGGER = logging.getLogger(__name__)

class ZodiacHomeAssistant:

    ZODIAC_HASS_ID = "zodiac_tri_expert_chlorinator"

    def __init__(self, config_file_path : Path = "config.yaml"):
        
        ######################################################################
        # Load config file
        ######################################################################
        _LOGGER.info(f"Loading config file at: {config_file_path}")
        with open(config_file_path, 'r') as f:
            config = yaml.safe_load(f)
        
        _LOGGER.debug(f"Loaded config: {config}")
        try:
            mqtt_host     = config["mqtt"]["host"]

        except KeyError:
            _LOGGER.error("Error loading config file, host field is missing!")
            raise ConfigFileMalformed()
                                
        try:
            mqtt_port = int(config["port"])
        except KeyError:
            mqtt_port = 1883

        try:
            mqtt_username = config["mqtt"]["user"]
            mqtt_password = config["mqtt"]["password"]
        except KeyError:
            mqtt_username = None
            mqtt_password = None

        try:
            serial_port = config["zodiac"]["serial_port"]
        except KeyError:
            _LOGGER.error("Error loading config file, serial port path is missing!")
            raise ConfigFileMalformed()

        ######################################################################
        # Connect to MQTT broker
        ######################################################################
        _LOGGER.info(f"Launching MQTT client...")
        # Configure the required parameters for the MQTT broker
        self.mqtt_settings = Settings.MQTT(
            host     = mqtt_host,
            port     = mqtt_port,
            username = mqtt_username,
            password = mqtt_password
        )

        ######################################################################
        # Opening device communication
        ######################################################################
        self.aqualink = Aqualink(serial_port)
        connection_attempts = 0
        connected = False

        while not connected:
            try:
                self.aqualink.probe()
            except NoResponseException:
                connection_attempts += 1
                _LOGGER.warning(f"No response from Zodiac, attempt {connection_attempts}/{MAX_CONNECTION_ATTEMPTS}!")

                if connection_attempts == MAX_CONNECTION_ATTEMPTS:
                    _LOGGER.error(f"Can't connect to Zodiac after {connection_attempts} tries!")
                    raise CantConnectToZodiac()
                else:
                    sleep(WAIT_BETWEEN_COMMANDS)
                    continue
            
            connected = True
        
        sleep(WAIT_BETWEEN_COMMANDS)
        zodiac_id = self.aqualink.get_id()

        ######################################################################
        # Build sensors
        ######################################################################
        _LOGGER.info(f"Creating sensors...")

        device_info = DeviceInfo(
            name         = "Zodiac SWG",
            model        = "TRi Expert",
            identifiers  = self.ZODIAC_HASS_ID,
            manufacturer = "ZODIAC POOL SOLUTIONS",
            sw_version   = zodiac_id,
        )
        

        s_connection_state_info     = BinarySensorInfo(name="Connection state", device_class="connectivity", unique_id=self.ZODIAC_HASS_ID + "_connected", device=device_info)
        s_connection_state_settings = Settings(mqtt=self.mqtt_settings, entity=s_connection_state_info)
        s_connection_state          = BinarySensor(s_connection_state_settings)
        s_connection_state.update_state(False)

        s_ph_setpoint_info          = SensorInfo(name = "pH setpoint", min = 6.8, max = 7.6, device_class = "ph", unique_id = self.ZODIAC_HASS_ID + "_ph_setpoint", device = device_info)
        s_ph_setpoint_settings      = Settings(mqtt = self.mqtt_settings, entity = s_ph_setpoint_info)
        s_ph_setpoint               = Sensor(s_ph_setpoint_settings)
        # s_ph_setpoint.set_state(7.0)

    def loop():
        while True:
            try:
                response = self.send_command(ProbeCommand())
                assert isinstance(response, ProbeResponse), "Probe reponse incorrect type!"
            except (ResponseMalformedException, TimeoutError):
                _LOGGER.error("Error sending probe, retrying!")
                sleep(5)
                continue

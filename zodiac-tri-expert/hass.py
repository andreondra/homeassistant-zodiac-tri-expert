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
        _LOGGER.info(f"Connecting to Zodiac...")
        self.aqualink = Aqualink(serial_port)
        connection_attempts = 0
        connected = False

        while not connected:
            try:
                self.aqualink.probe()
                sleep(WAIT_BETWEEN_COMMANDS)
                _LOGGER.info(f"Getting Zodiac ID...")
                zodiac_id = self.aqualink.get_id()
                sleep(WAIT_BETWEEN_COMMANDS)
            except NoResponseException:
                connection_attempts += 1
                _LOGGER.warning(f"No response from Zodiac, attempt {connection_attempts}/{MAX_CONNECTION_ATTEMPTS}!")

                if MAX_CONNECTION_ATTEMPTS != 0 and connection_attempts == MAX_CONNECTION_ATTEMPTS:
                    _LOGGER.error(f"Can't connect to Zodiac after {connection_attempts} tries!")
                    raise CantConnectToZodiac()
                else:
                    sleep(WAIT_BETWEEN_COMMANDS)
                    continue
            
            connected = True

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
        self.s_connection_state     = BinarySensor(s_connection_state_settings)
        self.s_connection_state.on()

        s_ph_setpoint_info          = SensorInfo(name = "pH setpoint", min = 6.8, max = 7.6, state_class = "measurement", device_class = "ph", unique_id = self.ZODIAC_HASS_ID + "_ph_setpoint", device = device_info)
        s_ph_setpoint_settings      = Settings(mqtt = self.mqtt_settings, entity = s_ph_setpoint_info)
        self.s_ph_setpoint          = Sensor(s_ph_setpoint_settings)

        s_ph_current_info           = SensorInfo(name = "Current pH", min = 0, max = 14, state_class = "measurement", device_class = "ph", unique_id = self.ZODIAC_HASS_ID + "_ph_current", device = device_info)
        s_ph_current_settings       = Settings(mqtt = self.mqtt_settings, entity = s_ph_current_info)
        self.s_ph_current           = Sensor(s_ph_current_settings)

        s_acl_setpoint_info         = SensorInfo(name = "ACL setpoint", min = 600, max = 800, state_class = "measurement", unique_id = self.ZODIAC_HASS_ID + "_acl_setpoint", device = device_info)
        s_acl_setpoint_settings     = Settings(mqtt = self.mqtt_settings, entity = s_acl_setpoint_info)
        self.acl_setpoint           = Sensor(s_acl_setpoint_settings)

        s_acl_current_info          = SensorInfo(name = "Current ACL", min = 0, max = 1000, state_class = "measurement", unique_id = self.ZODIAC_HASS_ID + "_acl_current", device = device_info)
        s_acl_current_settings      = Settings(mqtt = self.mqtt_settings, entity = s_acl_current_info)
        self.s_acl_current          = Sensor(s_acl_current_settings)

        _LOGGER.info(f"Setup done!")

    def loop(self):
        while True:
            try:
                status = self.aqualink.set_output_get_info(70)
            except NoResponseException:
                _LOGGER.warning("No response from Zodiac!")
                self.s_connection_state.off()
                sleep(WAIT_BETWEEN_COMMANDS)
                continue
            
            self.s_connection_state.on()
            self.s_ph_setpoint.set_state(status.ph_setpoint)
            self.s_ph_current.set_state(status.ph_current)
            self.acl_setpoint.set_state(status.acl_setpoint)
            self.s_acl_current.set_state(status.acl_current)
            sleep(10)
        
            


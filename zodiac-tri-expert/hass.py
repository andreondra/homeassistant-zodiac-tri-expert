from ha_mqtt_discoverable import Settings, DeviceInfo
from ha_mqtt_discoverable.sensors import BinarySensor, BinarySensorInfo, Sensor, SensorInfo, Number, NumberInfo
from paho.mqtt.client import Client, MQTTMessage

import yaml
from pathlib import Path
import logging
from time import sleep
import signal

from .constants  import *
from .exceptions import *
from .aqualink   import Aqualink

_LOGGER = logging.getLogger(__name__)

class ZodiacHomeAssistant:

    ZODIAC_HASS_ID = "zodiac_tri_expert_chlorinator"

    def __init__(self, config_file_path : Path = "config.yaml"):
        
        signal.signal(signal.SIGTERM, lambda s, f: self.sigterm_handler())
        signal.signal(signal.SIGINT,  lambda s, f: self.sigterm_handler())

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
        
        try:
            max_conn_attempts = config["zodiac"]["max_connection_attempts"]
        except KeyError:
            # Set to unlimited.
            max_conn_attempts = 0

        try:
            self.refresh_interval = int(config["mqtt"]["refresh_interval"])
        except KeyError:
            self.refresh_interval = 10
        except TypeError:
            _LOGGER.error("Refresh interval should be integer >= 10!")
            raise ConfigFileMalformed()

        if self.refresh_interval < 10:
            _LOGGER.error("Refresh interval should be integer >= 10!")
            raise ConfigFileMalformed()
        
        try:
            default_output_power = int(config["zodiac"]["default_power"])
        except KeyError:
            default_output_power = 70
        except TypeError:
            _LOGGER.error("Default output power should be integer in [0, 101]")
            raise ConfigFileMalformed()
    
        if default_output_power < 0 or default_output_power > 101:
            _LOGGER.error("Default output power should be integer in [0, 101]")
            raise ConfigFileMalformed()

        self.current_output_power = default_output_power

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
                _LOGGER.warning(f"No response from Zodiac, attempt {connection_attempts}/{max_conn_attempts if max_conn_attempts != 0 else 'unlimited'}!")

                if max_conn_attempts != 0 and connection_attempts == max_conn_attempts:
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

        s_acl_setpoint_info         = SensorInfo(name = "ACL setpoint", min = 600, max = 800, state_class = "measurement", unique_id = self.ZODIAC_HASS_ID + "_acl_setpoint", device = device_info, unit_of_measurement = "mV")
        s_acl_setpoint_settings     = Settings(mqtt = self.mqtt_settings, entity = s_acl_setpoint_info)
        self.acl_setpoint           = Sensor(s_acl_setpoint_settings)

        s_acl_current_info          = SensorInfo(name = "Current ACL", min = 0, max = 1000, state_class = "measurement", unique_id = self.ZODIAC_HASS_ID + "_acl_current", device = device_info, unit_of_measurement = "mV")
        s_acl_current_settings      = Settings(mqtt = self.mqtt_settings, entity = s_acl_current_info)
        self.s_acl_current          = Sensor(s_acl_current_settings)

        n_output_power_info         = NumberInfo(name = "Output power", min = 0, max = 101, mode = "slider", step = 1, unique_id = self.ZODIAC_HASS_ID + "_output_power", device = device_info, unit_of_measurement = "%")
        n_output_power_settings     = Settings(mqtt = self.mqtt_settings, entity = n_output_power_info)
        self.n_output_power         = Number(n_output_power_settings, lambda c, u, m: self.power_callback(c, m))
        self.n_output_power.set_value(self.current_output_power)

        _LOGGER.info(f"Setup done!")

    # To receive number updates from HA, define a callback function:
    def power_callback(self, client: Client, message: MQTTMessage):
        power = int(message.payload.decode())
        self.current_output_power = power
        _LOGGER.debug(f"Received output power = {power} % from HA.")
        # Send an MQTT message to confirm to HA that the number was changed
        self.n_output_power.set_value(power)

    def sigterm_handler(self):
        _LOGGER.info("Terminating connection to HA...")
        # Setting connection state to disconnected when shutting down the script.
        try:
            self.s_connection_state.off()
        except AttributeError:
            pass
        raise InterruptedError()

    def loop(self):

        current_fails = 0

        while True:
            try:
                status = self.aqualink.set_output_get_info(self.current_output_power)
            except NoResponseException:
                current_fails += 1
                _LOGGER.warning(f"No response from Zodiac! Currently {current_fails} fails.")
                
                if current_fails > CONN_DEAD_THRESH:
                    self.s_connection_state.off()

                sleep(WAIT_BETWEEN_COMMANDS)
                continue
            
            current_fails = 0
            self.s_connection_state.on()
            self.s_ph_setpoint.set_state(status.ph_setpoint)
            self.s_ph_current.set_state(status.ph_current)
            self.acl_setpoint.set_state(status.acl_setpoint)
            self.s_acl_current.set_state(status.acl_current)
            sleep(self.refresh_interval)
        
            


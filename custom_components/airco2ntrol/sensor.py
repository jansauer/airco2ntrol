"""Sensors for the AIRCO2NTROL sensor integration."""

from datetime import timedelta
import fcntl
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import (DEVICE_CLASS_TEMPERATURE, TEMP_CELSIUS)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (DOMAIN, DEFAULT_DEVICE)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_devices, discovery_info=None):
    _fp = open(DEFAULT_DEVICE, 'ab+', 0)
    key = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]
    set_report = bin(0x00) + "".join(chr(e) for e in key)
    HIDIOCSFEATURE_9 = 0xC0094806
    fcntl.ioctl(_fp, HIDIOCSFEATURE_9, bytearray.fromhex('00 c4 c6 c0 92 40 23 dc 96'))
    
    async def async_update_data():
        """Poll latest sensor data."""
        result = {}
        for retry in range(10):              
            values = __poll()
            if 0x42 in values or 0x50 in values:
                if 0x42 in values:
                    result["temperature"] = f'{(values[0x42]/16.0-273.15):.2f}'
                if 0x50 in values:
                    result["carbonDioxide"] = values[0x50]
                break
        return result

    def __poll():
        data = list(e for e in _fp.read(8))
        # print(data)
        key = [0xc4, 0xc6, 0xc0, 0x92, 0x40, 0x23, 0xdc, 0x96]
        decrypted = __decrypt(key, data)
        # print(decrypted)
        if decrypted[4] != 0x0d or (sum(decrypted[:3]) & 0xff) != decrypted[3]:
            _LOGGER.info("Checksum error")
        else:
            op = decrypted[0]
            val = decrypted[1] << 8 | decrypted[2]
            return {op: val}

    def __decrypt(key, data):
        cstate = [0x48,  0x74,  0x65,  0x6D,  0x70,  0x39,  0x39,  0x65]
        shuffle = [2, 4, 0, 7, 1, 6, 5, 3]
        phase1 = [0] * 8
        for i, o in enumerate(shuffle):
            phase1[o] = data[i]
        phase2 = [0] * 8
        for i in range(8):
            phase2[i] = phase1[i] ^ key[i]
        phase3 = [0] * 8
        for i in range(8):
            phase3[i] = ( (phase2[i] >> 3) | (phase2[ (i-1+8)%8 ] << 5) ) & 0xff
        ctmp = [0] * 8
        for i in range(8):
            ctmp[i] = ( (cstate[i] >> 4) | (cstate[i]<<4) ) & 0xff
        out = [0] * 8
        for i in range(8):
            out[i] = (0x100 + phase3[i] - ctmp[i]) & 0xff	
        return out

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="AIRCO2NTROL",
        update_method=async_update_data,
        update_interval=timedelta(seconds=10),
    )

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    async_add_devices([
        Airco2ntrolCarbonDioxide(coordinator),
        Airco2ntrolTemperature(coordinator)
    ])


class Airco2ntrolCarbonDioxide(CoordinatorEntity, SensorEntity):
    """AIRCO2NTROL carbon dioxide sensor."""

    def __init__(self, coordinator):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'AirCO2ntrol Carbon Dioxide'

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.error("---------------")
        _LOGGER.error(self.coordinator)
        _LOGGER.error(self.coordinator.data)
        _LOGGER.error("++++++++++++++++")
        return self.coordinator.data["carbonDioxide"]

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return "ppm"

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return 'co2'

    @property
    def icon(self):
        """Return the icon of device based on its type."""
        return 'mdi:molecule-co2'


class Airco2ntrolTemperature(CoordinatorEntity, SensorEntity):
    """AIRCO2NTROL temperature sensor."""

    def __init__(self, coordinator):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'AirCO2ntrol Temperature'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self.coordinator.data["temperature"]

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def icon(self):
        """Return the icon of device based on its type."""
        return 'mdi:thermometer'

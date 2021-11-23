"""The AIRCO2NTROL sensor integration."""

from homeassistant.core import HomeAssistant

from .const import DOMAIN

async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Hello World component."""
    hass.data.setdefault(DOMAIN, {})

    return True

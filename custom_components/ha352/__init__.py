# -*- coding: utf-8 -*-
"""ha352: 352 智能家电（空气净化器/净饮机）Home Assistant 集成。"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import Ha352Client
from .const import CONF_ACCOUNT, CONF_AREA, CONF_PASSWORD, DOMAIN
from .coordinator import Ha352Coordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "fan", "switch", "light"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = Ha352Client(
        entry.data[CONF_ACCOUNT], entry.data[CONF_PASSWORD],
        area=entry.data.get(CONF_AREA, ""))
    coordinator = Ha352Coordinator(hass, client, entry.title)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok

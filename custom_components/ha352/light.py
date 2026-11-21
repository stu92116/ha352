# -*- coding: utf-8 -*-
"""灯平台：Z90 显示屏/指示灯（illumination，实测 0/1 双向生效）。"""
from __future__ import annotations

import logging

from homeassistant.components.light import (
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import Ha352Coordinator
from .entity import Ha352Entity, async_setup_platform_entities

_LOGGER = logging.getLogger(__name__)


class Ha352Light(Ha352Entity, LightEntity):
    """Z90 屏幕灯。"""

    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_color_mode = ColorMode.ONOFF
    _attr_translation_key = "display_light"

    def __init__(self, coordinator: Ha352Coordinator, iot_id: str) -> None:
        super().__init__(coordinator, iot_id)
        self._attr_unique_id = f"{iot_id}_illumination"

    @property
    def is_on(self) -> bool | None:
        value = self._props.get("illumination")
        if value is None:
            return None
        try:
            return int(value) > 0
        except (TypeError, ValueError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set({"illumination": 1})

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set({"illumination": 0})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: Ha352Coordinator = hass.data[DOMAIN][entry.entry_id]

    def _build(iot_id: str) -> list:
        props = coordinator.data[iot_id].get("props") or {}
        if "illumination" in props:
            return [Ha352Light(coordinator, iot_id)]
        return []

    async_setup_platform_entities(
        coordinator, entry.async_on_unload, async_add_entities, _build)

# -*- coding: utf-8 -*-
"""风扇平台（Z90 空气净化器）：开关 + 1-3 档风速。"""
from __future__ import annotations

import logging

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util.percentage import ordered_list_item_to_percentage, \
    percentage_to_ordered_list_item

from .const import DOMAIN
from .coordinator import Ha352Coordinator
from .entity import Ha352Entity, async_setup_platform_entities

_LOGGER = logging.getLogger(__name__)

PRESET_LEVELS = [1, 2, 3]  # WindSpeed 档位（TSL range 1-3，冒烟测试已确认）
PRESET_MODES = [f"{n}档" for n in PRESET_LEVELS]


class Ha352Fan(Ha352Entity, FanEntity):
    """Z90 净化器风扇。"""

    _attr_preset_modes = PRESET_MODES
    _attr_supported_features = FanEntityFeature.PRESET_MODE
    _attr_speed_count = len(PRESET_LEVELS)

    def __init__(self, coordinator: Ha352Coordinator, iot_id: str) -> None:
        super().__init__(coordinator, iot_id)
        self._attr_unique_id = f"{iot_id}_fan"
        self._attr_translation_key = "fan_speed"

    @property
    def is_on(self) -> bool | None:
        return self._props.get("PowerSwitch") == 1

    @property
    def preset_mode(self) -> str | None:
        level = self._props.get("WindSpeed")
        try:
            return f"{int(level)}档" if int(level) in PRESET_LEVELS else None
        except (TypeError, ValueError):
            return None

    @property
    def percentage(self) -> int | None:
        level = self._props.get("WindSpeed")
        try:
            level = int(level)
        except (TypeError, ValueError):
            return None
        if level not in PRESET_LEVELS:
            return None
        return ordered_list_item_to_percentage(PRESET_LEVELS, level)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs,
    ) -> None:
        if preset_mode is None and percentage is not None:
            preset_mode = f"{percentage_to_ordered_list_item(PRESET_LEVELS, percentage)}档"
        items: dict = {"PowerSwitch": 1}
        if preset_mode is not None and preset_mode in PRESET_MODES:
            items["WindSpeed"] = PRESET_MODES.index(preset_mode) + 1
        await self._async_set(items)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set({"PowerSwitch": 0})

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode not in PRESET_MODES:
            return
        await self._async_set({"PowerSwitch": 1, "WindSpeed": PRESET_MODES.index(preset_mode) + 1})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: Ha352Coordinator = hass.data[DOMAIN][entry.entry_id]

    def _build(iot_id: str) -> list:
        props = coordinator.data[iot_id].get("props") or {}
        if "PowerSwitch" in props:
            return [Ha352Fan(coordinator, iot_id)]
        return []

    async_setup_platform_entities(
        coordinator, entry.async_on_unload, async_add_entities, _build)

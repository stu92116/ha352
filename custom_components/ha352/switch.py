# -*- coding: utf-8 -*-
"""开关平台：Z90 功能开关 + 净饮机开关，按属性存在性动态生成。"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import Ha352Coordinator
from .entity import Ha352Entity, async_setup_platform_entities

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class SwitchDesc:
    key: str
    icon: str
    category: EntityCategory | None = None


SWITCH_DESCRIPTIONS: tuple[SwitchDesc, ...] = (
    SwitchDesc("UVLEDSwitch", "mdi:lightbulb-on"),
    SwitchDesc("PCISwitch", "mdi:atom"),
    SwitchDesc("SmartModeSwitch", "mdi:brain"),
    SwitchDesc("ChildLockSwitch", "mdi:lock"),
    SwitchDesc("voicesettings", "mdi:volume-high"),
    SwitchDesc("StandbySensorSwitch", "mdi:motion-sensor"),
    SwitchDesc("MicrowaveSensor", "mdi:radar"),
    SwitchDesc("SleepMode", "mdi:sleep"),
    SwitchDesc("HotPotSwitch", "mdi:kettle"),
    SwitchDesc("CoolPotSwitch", "mdi:cup-water"),
    SwitchDesc("UVC", "mdi:lightbulb-on"),
    SwitchDesc("DirectEffluentSwitch", "mdi:arrow-down-bold"),
    SwitchDesc("HolidayMode", "mdi:palm-tree"),
)


class Ha352Switch(Ha352Entity, SwitchEntity):
    def __init__(self, coordinator: Ha352Coordinator, iot_id: str, desc: SwitchDesc) -> None:
        super().__init__(coordinator, iot_id)
        self._desc = desc
        self._attr_unique_id = f"{iot_id}_{desc.key}"
        self._attr_translation_key = desc.key.lower()
        self._attr_icon = desc.icon
        self._attr_entity_category = desc.category

    @property
    def is_on(self) -> bool:
        return self._props.get(self._desc.key) == 1

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set({self._desc.key: 1})

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set({self._desc.key: 0})


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: Ha352Coordinator = hass.data[DOMAIN][entry.entry_id]

    def _build(iot_id: str) -> list:
        props = coordinator.data[iot_id].get("props") or {}
        return [
            Ha352Switch(coordinator, iot_id, desc)
            for desc in SWITCH_DESCRIPTIONS
            if desc.key in props
        ]

    async_setup_platform_entities(
        coordinator, entry.async_on_unload, async_add_entities, _build)

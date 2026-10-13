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
    name: str
    icon: str
    category: EntityCategory | None = None


SWITCH_DESCRIPTIONS: tuple[SwitchDesc, ...] = (
    SwitchDesc("UVLEDSwitch", "UV 杀菌灯", "mdi:lightbulb-on"),
    SwitchDesc("PCISwitch", "负离子", "mdi:atom"),
    SwitchDesc("SmartModeSwitch", "智能模式", "mdi:brain"),
    SwitchDesc("ChildLockSwitch", "童锁", "mdi:lock"),
    SwitchDesc("voicesettings", "语音提示", "mdi:volume-high"),
    SwitchDesc("StandbySensorSwitch", "待机感应", "mdi:motion-sensor"),
    SwitchDesc("MicrowaveSensor", "微波感应", "mdi:radar"),
    SwitchDesc("SleepMode", "睡眠模式", "mdi:sleep"),
    SwitchDesc("HotPotSwitch", "热罐开关", "mdi:kettle"),
    SwitchDesc("CoolPotSwitch", "冷罐开关", "mdi:cup-water"),
    SwitchDesc("UVC", "UV 杀菌", "mdi:lightbulb-on"),
    SwitchDesc("DirectEffluentSwitch", "直排开关", "mdi:arrow-down-bold"),
    SwitchDesc("HolidayMode", "假日模式", "mdi:palm-tree"),
)


class Ha352Switch(Ha352Entity, SwitchEntity):
    def __init__(self, coordinator: Ha352Coordinator, iot_id: str, desc: SwitchDesc) -> None:
        super().__init__(coordinator, iot_id)
        self._desc = desc
        self._attr_unique_id = f"{iot_id}_{desc.key}"
        self._attr_name = desc.name
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

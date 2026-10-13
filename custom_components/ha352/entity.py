# -*- coding: utf-8 -*-
"""实体基类与平台级动态发现辅助。"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Ha352Error
from .const import DOMAIN, MANUFACTURER, MODEL_NAMES, PRODUCT_KEY_MODEL
from .coordinator import Ha352Coordinator

_LOGGER = logging.getLogger(__name__)


def model_of(meta: dict, props: dict[str, Any]) -> str:
    """推断型号：固件名 NameByFirmware -> 固件版本串 -> productKey 映射表。"""
    fw = str(props.get("NameByFirmware") or "")
    for key in MODEL_NAMES:
        if key in fw:
            return key
    hw = str(props.get("HardwareFirmwareVersion") or "")
    for key in MODEL_NAMES:
        if key in hw:
            return key
    pk = str(meta.get("productKey") or "")
    return PRODUCT_KEY_MODEL.get(pk) or pk or fw or "352"


def device_name(meta: dict, props: dict[str, Any]) -> str:
    model = model_of(meta, props)
    label = MODEL_NAMES.get(model)
    if label:
        return f"352 {model}"
    mac = str(meta.get("deviceName") or iot_id_short(meta))
    return f"352 {mac}"


def iot_id_short(meta: dict) -> str:
    iot_id = str(meta.get("iotId") or "")
    return iot_id[:6] if iot_id else "device"


class Ha352Entity(CoordinatorEntity[Ha352Coordinator], Entity):
    """所有 352 实体的公共基类。"""

    _attr_has_entity_name = True

    def __init__(self, coordinator: Ha352Coordinator, iot_id: str) -> None:
        super().__init__(coordinator)
        self.iot_id = iot_id

    # ---- coordinator 数据快捷访问 ----

    @property
    def _entry(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self.iot_id) or {}

    @property
    def _props(self) -> dict[str, Any]:
        return self._entry.get("props") or {}

    @property
    def _meta(self) -> dict:
        return self._entry.get("meta") or {}

    @property
    def available(self) -> bool:
        return bool(self.coordinator.last_update_success and self._entry.get("online"))

    @property
    def device_info(self) -> DeviceInfo:
        props = self._props
        meta = self._meta
        sw = str(props.get("HardwareFirmwareVersion") or "")
        return DeviceInfo(
            identifiers={(DOMAIN, self.iot_id)},
            name=device_name(meta, props),
            manufacturer=MANUFACTURER,
            model=model_of(meta, props),
            sw_version=sw or None,
        )

    async def _async_set(self, items: dict[str, Any]) -> None:
        """写属性，等设备上报后刷新（实测上报约滞后 1-2s）。"""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_properties, self.iot_id, items)
        await asyncio.sleep(2)
        await self.coordinator.async_request_refresh()


def async_setup_platform_entities(
    coordinator: Ha352Coordinator,
    entry_unload: Callable[[Callable[[], None]], None],
    async_add_entities: Callable[[list[Entity]], None],
    builder: Callable[[str], list[Entity]],
) -> None:
    """按 coordinator 数据动态发现设备：新 iot_id 出现时由 builder 生成实体。

    builder 只在设备首次出现时调用一次；离线设备（无属性）跳过，
    待其上线后下一轮自动补建。
    """
    added: set[str] = set()

    def _discover() -> None:
        data = coordinator.data or {}
        new_ids = [k for k in data if k not in added]
        entities: list[Entity] = []
        for iot_id in new_ids:
            added.add(iot_id)
            try:
                entities.extend(builder(iot_id))
            except Exception:  # noqa: BLE001 - 单设备异常不拖垮其它设备
                _LOGGER.exception("ha352 构建 %s 实体失败", iot_id)
        if entities:
            async_add_entities(entities)

    _discover()
    entry_unload(coordinator.async_add_listener(_discover))

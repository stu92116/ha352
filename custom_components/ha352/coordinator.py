# -*- coding: utf-8 -*-
"""数据协调器：60s 轮询设备列表 + 每设备属性。"""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Ha352AuthError, Ha352Client, Ha352Error
from .const import UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class Ha352Coordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """data 结构: {iot_id: {"meta": 设备元数据, "props": {identifier: value}, "online": bool}}"""

    def __init__(self, hass: HomeAssistant, client: Ha352Client, entry_title: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{entry_title} (ha352)",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
            request_refresh_debouncer=None,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            devices = await self.hass.async_add_executor_job(self.client.list_devices)
        except Ha352AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except Ha352Error as err:
            raise UpdateFailed(str(err)) from err

        data: dict[str, dict[str, Any]] = {}
        for meta in devices:
            iot_id = str(meta["iotId"])
            online = self.client.is_online(meta)
            props: dict[str, Any] = {}
            if online:
                try:
                    props = await self.hass.async_add_executor_job(
                        self.client.get_properties, iot_id)
                except Ha352Error as err:
                    _LOGGER.warning("352 设备 %s 属性读取失败: %s", iot_id, err)
                    online = False
            data[iot_id] = {"meta": meta, "props": props, "online": online}
        return data

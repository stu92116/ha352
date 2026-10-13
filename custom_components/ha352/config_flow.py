# -*- coding: utf-8 -*-
"""UI 配置流：输入 352 账号密码，验证后创建集成条目。"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from .api import Ha352AuthError, Ha352Client, Ha352ConnectionError, Ha352Error
from .const import CONF_ACCOUNT, CONF_PASSWORD, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ACCOUNT): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """真实登录 + 拉设备列表验证凭据（在线程池执行，网络调用是阻塞的）。"""
    client = Ha352Client(data[CONF_ACCOUNT], data[CONF_PASSWORD])
    try:
        devices = await hass.async_add_executor_job(client.list_devices)
    except Ha352AuthError as err:
        raise Ha352AuthError(str(err)) from err
    except Ha352ConnectionError as err:
        raise Ha352ConnectionError(str(err)) from err
    return {"devices": len(devices), "account": data[CONF_ACCOUNT]}


class Ha352ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """处理集成添加流程。"""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except Ha352AuthError:
                errors["base"] = "invalid_auth"
            except Ha352ConnectionError:
                errors["base"] = "cannot_connect"
            except Ha352Error:
                errors["base"] = "unknown"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("352 添加流程意外错误")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(info["account"])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{DEFAULT_NAME} {info['account']}", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """登录态失效后的重新认证。"""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        assert self._reauth_entry is not None
        if user_input is not None:
            data = {**self._reauth_entry.data, **user_input}
            try:
                await validate_input(self.hass, data)
            except Ha352AuthError:
                errors["base"] = "invalid_auth"
            except Ha352ConnectionError:
                errors["base"] = "cannot_connect"
            except Ha352Error:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_finish(
                    self._reauth_entry, data=data)
        schema = vol.Schema({
            vol.Required(CONF_ACCOUNT,
                         default=self._reauth_entry.data.get(CONF_ACCOUNT, "")): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        })
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=schema, errors=errors)

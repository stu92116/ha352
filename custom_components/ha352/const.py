# -*- coding: utf-8 -*-
"""ha352 常量。"""
from __future__ import annotations

DOMAIN = "ha352"
MANUFACTURER = "352"
DEFAULT_NAME = "352 Smart Home"

CONF_ACCOUNT = "account"
CONF_PASSWORD = "password"

UPDATE_INTERVAL_SECONDS = 60
REQUEST_TIMEOUT = 20

# 属性 -> 设备型号中文名（NameByFirmware 包含 key 时命中）
MODEL_NAMES: dict[str, str] = {
    "Z90": "空气净化器 Z90",
    "C925H": "净饮机 C925H",
    "B425H": "净饮机 B425H",
}

# productKey -> 型号（NameByFirmware 缺失时的兜底，Z90 无该属性）
PRODUCT_KEY_MODEL: dict[str, str] = {
    "a1o2ZnhLc0x": "Z90",
    "a1Ktxpu7com": "C925H",
    "a11S8Iz0VGN": "B425H",
}

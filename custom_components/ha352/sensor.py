# -*- coding: utf-8 -*-
"""传感器平台：按设备实际存在的属性动态生成。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import Ha352Coordinator
from .entity import Ha352Entity, async_setup_platform_entities, model_of


@dataclass(frozen=True)
class SensorDesc:
    key: str
    unit: str | None = None
    unit_fn: Callable[[dict, dict], str | None] | None = None  # (props, meta) -> unit
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    icon: str | None = None
    category: EntityCategory | None = None
    precision: int | None = None
    value_fn: Callable[[Any], str | float | None] | None = None


def _enum(mapping: dict[int, str]) -> Callable[[Any], str]:
    return lambda v: mapping.get(v, str(v))


def _water_unit(props: dict, meta: dict) -> str:
    """水量单位：C925H 实测为 L（35.5T↔35470L），B425H 由纯废比推算为 mL。"""
    return "mL" if model_of(meta, props) == "B425H" else "L"


def _b425h_only(props: dict, meta: dict) -> str:
    return "mL" if model_of(meta, props) == "B425H" else None


# clang-format off
SENSOR_DESCRIPTIONS: tuple[SensorDesc, ...] = (
    # ---------------- Z90 空气净化器：环境 ----------------
    SensorDesc("PM25", unit="µg/m³",
               device_class=SensorDeviceClass.PM25, state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("PM10", unit="µg/m³",
               device_class=SensorDeviceClass.PM10, state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("HCHO", unit="µg/m³", icon="mdi:flask",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("TVOC", unit="µg/m³",
               device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("CurrentTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT, precision=1),
    SensorDesc("RelativeHumidity", unit="%",
               device_class=SensorDeviceClass.HUMIDITY,
               state_class=SensorStateClass.MEASUREMENT, precision=1),
    SensorDesc("airQualityGrade", icon="mdi:air-filter",
               value_fn=_enum({1: "优", 2: "良", 3: "轻度污染",
                               4: "中度污染", 5: "重度污染", 6: "严重污染"})),
    # ---------------- Z90：状态/累计 ----------------
    SensorDesc("WorkMode", icon="mdi:cog",
               value_fn=_enum({0: "待机", 1: "自动"})),
    SensorDesc("WindValue", category=EntityCategory.DIAGNOSTIC),
    SensorDesc("DeviceMode", category=EntityCategory.DIAGNOSTIC,
               icon="mdi:tune"),
    SensorDesc("TotalPurAirV", unit="m³", icon="mdi:fan",
               state_class=SensorStateClass.TOTAL),
    SensorDesc("TotalRunTime", unit="min", icon="mdi:timer-outline",
               state_class=SensorStateClass.TOTAL),
    SensorDesc("SleepModeSetParam",
               category=EntityCategory.DIAGNOSTIC, icon="mdi:sleep"),
    SensorDesc("WiFI_RSSI", unit="dBm", icon="mdi:wifi",
               category=EntityCategory.DIAGNOSTIC),
    # ---------------- 滤芯（1-3，按存在性生成） ----------------
    SensorDesc("FilterLifeTimePercent_1", unit="%", icon="mdi:filter",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("FilterLifeTimePercent_2", unit="%", icon="mdi:filter",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("FilterLifeTimePercent_3", unit="%", icon="mdi:filter",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("FilterSN_1", icon="mdi:barcode",
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("FilterSN_2", icon="mdi:barcode",
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("FilterSN_3", icon="mdi:barcode",
               category=EntityCategory.DIAGNOSTIC),
    # ---------------- C925H/B425H 净饮机：水质 ----------------
    SensorDesc("RawWaterTDS", unit="ppm", icon="mdi:water-opacity",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("FinishedWaterTDS", unit="ppm", icon="mdi:water-check",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("RawWaterstatus", icon="mdi:water-alert",
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("PureWasteRatio", icon="mdi:swap-horizontal",
               category=EntityCategory.DIAGNOSTIC, precision=1),
    # ---------------- 净饮机：温度 ----------------
    SensorDesc("HotPotTemp", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("TapTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("TapFinishedWaterTemp", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("NormalTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("RawWaterTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("WaterTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("CoolPotTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("BoilingTemperature", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("RefluxNtcTemp", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("DisinfectionNtcTemp", unit="°C",
               device_class=SensorDeviceClass.TEMPERATURE,
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("SetTemperature", unit="°C", icon="mdi:thermometer",
               category=EntityCategory.DIAGNOSTIC),
    # ---------------- 净饮机：水量 ----------------
    SensorDesc("TotalWaterConsumption", unit_fn=_water_unit,
               icon="mdi:water", state_class=SensorStateClass.TOTAL_INCREASING),
    SensorDesc("TotalPureWater", unit_fn=_water_unit,
               icon="mdi:water-plus", state_class=SensorStateClass.TOTAL_INCREASING),
    SensorDesc("TotalWasteWater", unit_fn=_water_unit,
               icon="mdi:water-remove", state_class=SensorStateClass.TOTAL_INCREASING),
    SensorDesc("NormothermiaWater", unit_fn=_water_unit,
               icon="mdi:cup-water", state_class=SensorStateClass.TOTAL),
    SensorDesc("HydrothermalWater", unit_fn=_water_unit,
               icon="mdi:coffee", state_class=SensorStateClass.TOTAL),
    SensorDesc("SurplusWater_1", unit="L", icon="mdi:filter",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("SurplusWater_2", unit="L", icon="mdi:filter",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("CurrentPureWaterProduction", unit_fn=_water_unit,
               icon="mdi:water-boiler", state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("OneWater", unit="mL", icon="mdi:glass-water",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("OnePureWater", unit="mL", icon="mdi:water-boiler",
               state_class=SensorStateClass.MEASUREMENT),
    SensorDesc("OneWaterTime", unit="s",
               category=EntityCategory.DIAGNOSTIC, icon="mdi:timer"),
    SensorDesc("LiquidLevelStatus", unit="%", icon="mdi:gauge",
               state_class=SensorStateClass.MEASUREMENT),
    # ---------------- 净饮机：状态 ----------------
    SensorDesc("WorkState", icon="mdi:state-machine",
               value_fn=_enum({0: "待机", 1: "制水中"})),
    SensorDesc("HotPotState", icon="mdi:kettle",
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("HeatingStatus", icon="mdi:fire",
               value_fn=_enum({0: "未加热", 1: "加热中"})),
    SensorDesc("TotalWaterUsageDuration", unit="h",
               icon="mdi:history", category=EntityCategory.DIAGNOSTIC,
               state_class=SensorStateClass.TOTAL),
    SensorDesc("DeviceUsedTime", unit="h", icon="mdi:history",
               category=EntityCategory.DIAGNOSTIC,
               state_class=SensorStateClass.TOTAL),
    SensorDesc("CycleDisinfectTime", icon="mdi:dishwasher",
               category=EntityCategory.DIAGNOSTIC),
    SensorDesc("ErrorCode", icon="mdi:alert-circle",
               category=EntityCategory.DIAGNOSTIC),
)
# clang-format on


class Ha352Sensor(Ha352Entity, SensorEntity):
    """单属性传感器。"""

    def __init__(self, coordinator: Ha352Coordinator, iot_id: str, desc: SensorDesc) -> None:
        super().__init__(coordinator, iot_id)
        self._desc = desc
        self._attr_unique_id = f"{iot_id}_{desc.key}"
        self._attr_translation_key = desc.key.lower()

    @property
    def native_value(self) -> str | float | None:
        value = self._props.get(self._desc.key)
        if value is None or value == "":
            return None
        if self._desc.value_fn is not None:
            try:
                return self._desc.value_fn(value)
            except Exception:  # noqa: BLE001
                return str(value)
        if isinstance(value, bool):
            return int(value)
        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        if self._desc.unit_fn is not None:
            return self._desc.unit_fn(self._props, self._meta)
        return self._desc.unit

    @property
    def device_class(self):
        return self._desc.device_class

    @property
    def state_class(self):
        return self._desc.state_class

    @property
    def suggested_display_precision(self) -> int | None:
        return self._desc.precision

    @property
    def icon(self):
        return self._desc.icon

    @property
    def entity_category(self):
        return self._desc.category


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    coordinator: Ha352Coordinator = hass.data[DOMAIN][entry.entry_id]

    def _build(iot_id: str) -> list:
        props = coordinator.data[iot_id].get("props") or {}
        return [
            Ha352Sensor(coordinator, iot_id, desc)
            for desc in SENSOR_DESCRIPTIONS
            if desc.key in props
        ]

    async_setup_platform_entities(
        coordinator, entry.async_on_unload, async_add_entities, _build)

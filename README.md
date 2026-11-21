# 352 Smart Home for Home Assistant

非官方 Home Assistant 集成，通过 **352Life 云端 API** 接入 352（三个爸爸）空气净化器与净饮机，
支持 HA 原生 UI 配置、设备自动发现、HomeKit Bridge 转接 Apple TV 家庭 App。

> 协议来源：352Life Android APK 1.8.0 静态逆向 + 真实账号实测（2026-10）。
> 链路：352 REST 登录 → 阿里 OpenAccount OAuth → 阿里 IoT 平台（api.link.aliyun.com）。

## 支持设备（已实测）

| 设备 | 型号 | 能力 |
|---|---|---|
| 空气净化器 | **Z90** | PM2.5/PM10/甲醛/TVOC/温湿度传感器、开关/1-3档风速、UV灯/负离子/童锁/语音/屏幕灯等控制 |
| 净饮机 | **C925H** | 原水/纯水 TDS、水温×7、累计水量、滤芯寿命、水位等传感器（只读） |
| 净饮机 | B425H | 同 C925H 属性集（设备离线时自动隐藏实体） |

其他 352 云端账号绑定的设备也会按属性自动生成对应实体。

## 安装

### 方式 A：HACS（推荐）

1. HACS → 右上角菜单 → **Add custom repository**（添加自定义存储库）
2. 仓库地址填本仓库，类别选 **Integration（集成）**
3. 点击安装，重启 Home Assistant

### 方式 B：手动

把 `custom_components/ha352/` 整个目录拷到 HA 配置目录的
`config/custom_components/ha352/`，重启 HA。

## 配置

重启后：**设置 → 设备与服务 → 添加集成 → 搜索 "352"**，
输入 352Life App 的登录手机号与密码即可。账号下所有设备自动出现。

如果在 352Life 选择台湾（+886）登录，请在电话区号栏输入 `+886`，手机号栏填写和 App 相同的 `09XXXXXXXX`。其他账号可按 App 填写区号，原来能登录的配置可将区号留空。

- 设备每 **60 秒** 云端轮询一次（352 云不支持本地/局域网控制）
- 登录令牌自动续期（iotToken 20h 内自动重建会话），无需干预
- 密码变更后集成会提示重新认证

## 淨水器儀表板卡片

`lovelace/ha352-purifier-card.js` 提供兩種版面，`classic` 為淺色總覽，`atelier` 為深色版並顯示 24 小時與 7 天的 TDS 趨勢。

1. 把 JS 檔案放在 HA 設定目錄的 `www/ha352-purifier-card.js`。
2. 在「設定 → 儀表板 → 資源」將 `/local/ha352-purifier-card.js` 加為「JavaScript 模組」。
3. 在儀表板新增手動卡片，並填入實際的實體 ID。

```yaml
type: custom:ha352-purifier-card
style: atelier
title: 廚房淨水
model: 352 A418H
entities:
  inlet: sensor.kitchen_purifier_inlet_tds
  outlet: sensor.kitchen_purifier_outlet_tds
  filter_1: sensor.kitchen_purifier_filter_1
  filter_2: sensor.kitchen_purifier_filter_2
  temperature: sensor.kitchen_purifier_water_temperature
```

`inlet` 和 `outlet` 為必填。暮光版可用 `photo: /local/kitchen.jpg` 加入自己的照片。點選一項讀值會開啟 HA 的實體詳情。

## 仪表盘卡片示例

在「调试-home」面板添加：

```yaml
type: vertical-stack
cards:
  - type: tile
    entity: fan.352_z90_风速
    name: 352 Z90 空气净化器
    features:
      - type: fan-speed
      - type: toggle
  - type: entities
    entities:
      - sensor.352_z90_pm2_5
      - sensor.352_z90_pm10
      - sensor.352_z90_甲醛
      - sensor.352_z90_tvoc
      - sensor.352_z90_温度
      - sensor.352_z90_湿度
      - switch.352_z90_uv_杀菌灯
      - switch.352_z90_负离子
  - type: entities
    title: 352 C925H 净饮机
    entities:
      - sensor.352_c925h_原水_tds
      - sensor.352_c925h_纯水_tds
      - sensor.352_c925h_热水温度
      - sensor.352_c925h_水箱水位
```

> 实体 ID 以实际生成结果为准（中文实体名会保留在 entity_id 中），编辑面板时在实体选择器里搜索 "352" 前缀挑选即可。
> 上 Apple TV：装 [HomeKit Bridge](https://www.home-assistant.io/integrations/homekit/) 集成后勾选这些设备即可。

## 已知限制

- 仅云端轮询（352 无开放本地协议），控制响应约 2-5 秒
- Z90 的 WindSpeed 档位为 1-3（设备上报实测）
- 净饮机 `SetTemperature` 等设定项暂未开放控制，仅显示

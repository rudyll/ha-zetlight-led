# 蓝图 / Blueprints

现成的 Home Assistant 自动化蓝图，位于
[`blueprints/automation/zetlight_led/`](../blueprints/automation/zetlight_led)。
蓝图的名字、说明、字段都是**中/英双语**；都用实体选择器，所以整缸联动的那几个
对**任何**有 `fan` 实体的造浪泵都适用（导入时自己选泵的实体）。

## 要手动导入吗？（是的）

**HACS 装的是"集成"，只会拷贝 `custom_components/`，不会自动安装蓝图。** 蓝图要
单独导入，两种方式：

- **一键导入（推荐）**：点下面每个蓝图的链接，会直接打开你 HA 的"导入蓝图"对话框、
  URL 已填好，确认即可。
- 手动：**设置 → 自动化与场景 → 蓝图 → 导入蓝图**，粘贴该文件的 GitHub 链接；
  或把文件复制到 `config/blueprints/automation/zetlight_led/`。

> 一键链接走 `my.home-assistant.io` 跳转，需要你在 HA 里启用过 My Home Assistant
> （默认开启）。导入后在 **设置 → 自动化 → 用蓝图创建自动化** 里选它、填实体。

## 只控制灯 / Light only

| 蓝图 | 作用 | 一键导入 |
|---|---|---|
| schedule_at_sun | 日程起点跟随日出/日落 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fschedule_at_sun.yaml) |
| acclimation_ramp | 每天抬高驯化比例并重应用预设 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Facclimation_ramp.yaml) |
| lightning_on_storm | 雷暴天**按随机间隔反复**放闪电 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Flightning_on_storm.yaml) |
| weather_dimming | **阴雨天自动调暗**灯(按天气设「调光比例」,每级可自定义) | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fweather_dimming.yaml) |
| moon_phase | 夜间**月光随真实月相**强弱(很微妙,图自然感) | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fmoon_phase.yaml) |

## 整缸（灯 + 造浪泵） / Whole-tank

针对 GTS 泵集成（`gts_wavepump`）：它的开/停和强度是 **`fan`** 实体
（`fan.turn_off` / `fan.set_percentage`），运行模式 `run_mode`（`tide` = 内置
昼夜曲线）、波形 `wave_mode`（`surge` / `turbulence` …）是 `select`。你在导入时
选实体，所以别的有 `fan` 实体的泵也能用。

| 蓝图 | 作用 | 一键导入 |
|---|---|---|
| whole_tank_feed | 灯喂食→泵暂停，喂完恢复 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_feed.yaml) |
| whole_tank_storm | 雷暴：随机间隔的「闪电 + 泵打大浪」一阵阵 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_storm.yaml) |
| whole_tank_day_night_flow | 日出强流、日落柔流 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_day_night_flow.yaml) |
| whole_tank_maintenance | 开关：停泵 + 灯全白（换水） | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_maintenance.yaml) |
| whole_tank_acclimation | **整缸驯化**:每天同时升灯「调光比例」+泵「潮汐强度」 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_acclimation.yaml) |
| whole_tank_weather_dimming | **整缸天气调暗**:按天气同时调灯+泵强度 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_weather_dimming.yaml) |

## 整缸蓝图是"开放模板"，别被字段框死

- **造浪泵(fan) 是可选的**：`whole_tank_feed` / `whole_tank_maintenance` / `whole_tank_storm`
  里的"造浪泵(fan)"都可留空。没有能 BLE/WiFi 调速的造浪泵也能用这些蓝图
  （storm 留空就是"纯闪电"风暴）。
- **"额外断电设备"槽位**（feed / maintenance）：可留空、**可多选、不限类型**。用来接
  那些**不能蓝牙/WiFi 控、只能切总电源**的设备——最典型的就是**回水泵**（正常海缸
  一定有），还有加热棒等，插在智能插座/继电器上即可。喂食/维护开始时它们一起断电、
  结束再上电（走 `homeassistant.turn_off/on`，所以 switch、光、泵……哪种域都行）。
  > 注意：我们**不按名字猜设备**——"造浪泵"≠"回水泵"，一切都由你在下拉里自己选。
- **导入后还能自己改**：蓝图只是模板。导入后在 **设置 → 自动化 → 用蓝图创建** 建出
  自动化，再点右上角"**编辑为 YAML / Edit in YAML**"，就能继续往里加我们没预设的
  设备、开关或步骤。字段只是常用项，不是上限。
- `whole_tank_day_night_flow` / `whole_tank_acclimation` 调的是**强度**（百分比曲线），
  哑开关做不了强度，所以这两个**不提供**电源断电槽位——要联动回水泵这类设备，用
  feed/maintenance 的"额外断电设备"。

## 驯化的两种方式

- **「调光比例」number(我们的方案,推荐、透明可控)**:一个 0–100% 旋钮,在你现有
  日程上整体叠加缩放(保留曲线、可逆、100% 还原)。既能做**天气调暗**(weather_dimming
  蓝图),也能做**驯化**(acclimation_ramp 蓝图逐日升到 100)。这是同一个旋钮,一次用
  于一个目的即可。
- **「珊瑚驯化(原生)」switch + 「驯化天数」sensor(设备自带)**:开关一下,设备自己
  按天数(1–10)渐进,不改你的日程。**但它是厂家黑盒**——没有百分比、看不到总共几天、
  也不确定第 10 天是否自动恢复(我只解出了开关和天数计数)。想要透明可控就用上面的
  「调光比例」。

> **驯化基线提示**:灯的「调光比例」和泵的「潮汐强度」都是在**"当前处于 100%"**时把
> 当前曲线/日程当作基线。所以**首次下调驯化前**,请先确保灯是你的满配置日程、泵潮汐
> 强度在 100%;这样逐日升回 100% 才能精确还原。要改日程/曲线本身,也请在 100% 状态下改。

## 风暴节奏说明(频率/随机)

雷暴类蓝图是**天气进入雷暴状态后循环造风暴,直到天气转好自动停止**,不是只触发一次、
也不是固定节拍:

- `lightning_on_storm`(只灯):按随机间隔反复放闪电。间隔在"最短/最长间隔"里设
  (默认 20–90 秒随机)。
- `whole_tank_storm`(灯+泵):**一阵阵**地来——每阵 = 放闪电 + 泵切浪涌/乱流拉满
  **打一阵大浪**(随机时长,默认 8–20 秒),然后回落到平缓流一段(随机间隔,默认
  30–90 秒),如此反复。大浪强度、平缓强度、每阵时长、间隔都可在字段里调。

> 天气数据来自 HA 的天气集成(Met.no / 和风等),本集成没有自己的天气源。灯的
> 闪电/云彩是手动按钮,这些蓝图才是把它们接到天气、太阳和泵上的东西。

## Unified feeding and maintenance v2 (opt-in, current household staged OFF)

`whole_tank_modes_v2.yaml` coordinates native feed and maintenance through one
owner. Select an input_boolean maintenance helper, a separate persistent lamp
restore marker, explicit native feed button/flow sensor, and confirmed supply
entities. A DualKey raw button is a momentary event source, not the persistent
maintenance switch for this dropdown. Do not enable this together with the old
feeding/maintenance owners; keep original configs for rollback.

Maintenance: stop wave/lamp, stop skimmer, confirm reported off (10s timeout),
then cut return. Normal restore: return first; confirm reported on (10s timeout),
wait selected settle duration (this household30s), recheck modes and return, then
start skimmer. Unknown modes do not restore supplies. Both modes off are required
for normal restoration; maintenance wins over feeding. If a related acknowledgement
fails, leave the dependent action undone and raise an automation trace error.

HA relay state is not measured water level/flow. There is no level sensor and
no automatic maintenance expiry. A restart can restart the conservative wait.
Only lamp power ownership is retained; normal supply restoration assumes wave,
skimmer and return should be on, not arbitrary manual-off snapshots. A lamp off
before maintenance stays off; owned restoration uses retained mode/current program,
not a saved manual-slider brightness. Heater/master/unknown endpoints are unbound.

Local17 template tests and HA schema checks are software evidence only; household
configuration is still staged off. No live maintenance or supply-cycle acceptance.

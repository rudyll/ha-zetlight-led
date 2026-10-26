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
| whole_tank_weather_dimming | **旧版整缸天气调暗**：灯和泵共用百分比；保留兼容，独立配置请用 v2 | [导入](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Frudyll%2Fha-zetlight-led%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fzetlight_led%2Fwhole_tank_weather_dimming.yaml) |

## 日常基线加增益：源码修正候选（2026-10-26）

Rudy确认日常潮汐曲线已经调好：晴天应保持100%，天气恶劣时叠加增益，而不是先将
晴天降到80再恢复100。前一版草稿不符合这个意图；下节旧草稿表保留为历史／现场状态，
不能当成最新候选规则。

源码候选分别设置：晴天100、多云100、阴天100、雨雪110、大风115、暴雨120、
雷暴130，增益上限130（可设10–200）。这些只是待核定的示例，不是实际设备配置。
例如日常某段设置60，120%目标为72；每个时段从原始基线重新计算，回到100精确恢复。
各结果仍受GTS既有原始功率上限99限制，削顶时峰值会变平；软件上限不是缸的安全流量。
设置刻度增加20%也不证明实际流量增加20%。修改日常曲线前应先恢复100，避免混淆基线。

需要配套GTS-R10增益源码实现（尚未发布新的HACS版本）（实体范围10–200），已发布0.6.2仍最多100。
天气候选检查实体实际max，超出能力时跳过泵写入，灯光分支独立；不会悄悄把130当100。
本次GitHub更新仅同步配套源码与测试，**未更新HA蓝图或草稿、未部署GTS、未发布新的HACS版本**。
当前HA两条关闭草稿仍是此前版本。固定65/45的手动风暴还须改为从日常基线计算，
此前风暴候选不能直接与本次增益规则一起启用；后续F26-P01负责该项及联合验收。

## 整缸联动：天气 v2（灯光与造浪独立）

整缸模板统一显示为“**整缸联动 — …**”，表示珊瑚灯、造浪泵或已选供电设备的联动，
不再冠以积光品牌。只控制积光灯的模板保留品牌名。已有自动化的自定义名称不会随之改名。

新模板 [`whole_tank_weather_v2.yaml`](../blueprints/automation/zetlight_led/whole_tank_weather_v2.yaml)
源码已推送到GitHub；家庭HA已建立关闭状态的候选自动化，尚未启用。没有发布新的HACS集成版本。旧模板文件和输入含义保留不变。

| 天气 | 灯光调光比例 | 造浪潮汐曲线比例 |
| --- | ---: | ---: |
| 晴天／晴夜 | 100% | 80% |
| 多云 | 90% | 80% |
| 阴天／雾 | 75% | 80% |
| 雨／雪 | 60% | 90% |
| 大风 | 75% | 90% |
| 暴雨／冰雹 | 50% | 95% |
| 雷暴 | 50% | 100% |

以上为**此前已保存到HA的关闭草稿初值**，其造浪策略已被上节本地增益修正取代。不是 Rudy 的实际运行设置，也未通过任何缸的实机强度验收。
灯和泵各有七档输入，互不套用。造浪是既有潮汐曲线的10–100%缩放，并不是每时段的
泵功率；100%恢复基线，不能超过基线。独立上限约束所有天气的潮汐缩放，按5%向下取整。
雷暴时的手动间歇大浪由风暴蓝图单独控制，这里的上限不限制其大浪强度。

填写天气、珊瑚灯及调光比例、GTS造浪泵及潮汐强度、运行模式、实际流态，以及喂食开关、
维护开关、维护灯光恢复标记。恢复标记使用整缸喂食维护v2的同一个标记，不是新建另一套
维护所有权。只在三个模式／恢复输入都明确关闭时写入；缺测或进行中均不写。

- 灯已开启且处于日程模式时调光，不开灯、不覆盖观赏／手动／喂食；待恢复的日程写入不覆盖。
- 泵已开启、运行模式为tide且流态明确正常时才调整潮汐曲线，不开泵、不切模式、不覆盖原生喂食或手动风暴。
- 天气缺测、未识别或exceptional时保持现状。一个目标离线或写入失败，另一目标仍可独立处理；同值不重复写。
- 天气转晴按所配晴天档恢复；喂食／维护／恢复标记结束、设备重新上线或手动风暴回到tide时，按当前天气重新核对。
- 无法确认设备状态时不补猜，不启动定时重试；服务失败保留HA自动化跟踪可见性，下次相关状态变化再核对。

迁移前停用占用同一比例实体的旧整缸天气、只灯天气调暗或驯化自动化，保留配置备份，
再选择基线、上限和各天气档。新版不会自动修改已有自动化，也不会把既有95%手动风暴
强度当成已确认安全值。旧版风暴蓝图仍是独立所有者，不能因为本模板有保护就认为旧版也有互锁。
新风暴v2的互锁和接管恢复见下一节。停用本模板不会自动恢复比例，须先选定恢复值。

## 整缸联动：风暴 v2（喂食维护互锁）

[`whole_tank_storm_v2.yaml`](../blueprints/automation/zetlight_led/whole_tank_storm_v2.yaml)
新增独立的风暴强度上限、持久接管标记和喂食／维护／恢复互锁。旧版风暴文件保留。
只接管tide或本自动化已接管的manual；退出后只恢复自己接管的泵到tide，不启动已关闭的设备。
每次设备命令前及等待期间重查状态；已经发出的一次闪电／命令不能撤销。

模板默认大浪65、平缓45、上限65，持续8–12秒、间隔90–180秒，只对lightning和
lightning-rainy执行。均为草稿值，未实机验收；风暴的fan百分比与天气潮汐缩放不是同一刻度。
固定强度不会随夜间潮汐自动下降，也不保证平均流量比日常更大。启用前确认基线、夜间策略
和实际强度。闪电沿用灯的现有参数，并未在这里降低；灯已开且日程模式才闪电。

专用input_boolean记录风暴是否接管过泵，默认关闭，只供一条风暴自动化使用，不手动打开。
喂食／维护／恢复中不接管或恢复；服务失败保留标记并在HA跟踪中报错，不承诺无限重试。
停用／删除前，先在条件允许时退出风暴并确认潮汐恢复、接管标记已清除。不可并行启用旧版风暴。

### 保存自动化前检查全局重载事件

已观察到：HA2026.10.4按ID保存只加载该自动化，但仍广播automation_reloaded；另一条
监听该事件的自动化可以被重触发。不能仅凭“定向加载”承诺其他任务的等待计时完全不变。

1. 保存前检查既有automation_reloaded事件监听者及其当前动作、等待期限。
2. 若重触发会改变正在执行的控制／恢复，应等待合适时机或取得该影响的明确授权。
3. 批量准备后一次性安排变更；保存后比较监听者trace/last_triggered以及设备状态，不能只看current计数。
4. 个人自动化实体绑定放在本地.private或HA私有备份，不发布到公共仓库。

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

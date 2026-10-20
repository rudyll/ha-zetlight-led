# 抓包步骤 / Capture guide

目标：抓到在 Horizon Aqua App 里点某个功能时，手机发往灯
（`10.10.10.138:8855` UDP）的那条 `EE…CC` 帧的 **hex**，用于把该功能做进集成。

> 协议帧格式见 [`m5-light-protocol.md`](m5-light-protocol.md)；要抓的功能清单（F5–F12）见 [`roadmap.md`](roadmap.md)。

## 通用原则

- **一次只点一个功能**，点完等 1–2 秒再点下一个，并记下顺序，这样每条帧能对应上一个动作。
- 抓的时候让灯**别处于自动过渡**（渐变进行中会有连续 `0x13` 帧干扰）。
- 关键是**出站**（手机 → `10.10.10.138:8855`）那条帧；有回包（`DD…CC`）一起给我更好。
- 把 payload 的 hex 原样贴给我（例如 `EE000601023A011F21CC`），并注明是哪个动作。

## 方法 A：手机上抓（推荐，不挑网络拓扑，免 root）

用 **PCAPdroid**（Play 商店 / F-Droid 都有，基于 VPN API，无需 root）：

1. 打开 PCAPdroid → **Target app** 选 Horizon Aqua（`com.zetlightgoogle`）。
2. 点 **Start**，授予 VPN 权限。
3. 回到 Horizon Aqua，**点一个要抓的功能**（如「闪电」），等 1–2 秒。
4. 回 PCAPdroid 点 **Stop**。
5. 看 **Connections** 里到 `10.10.10.138:8855` 的 UDP，展开看 payload 的 HEX；
   或 **Export PCAP** 用 Wireshark 打开，过滤 `udp.port==8855`，
   右键某包 → Copy → 复制字节，取 UDP 数据区的 hex。

### iPhone（无 PCAPdroid）：用 Mac 的 RVI 抓

PCAPdroid 只有 Android 版。iPhone 用数据线连 Mac，走 Apple 的远程虚拟接口
（`rvictl` 随 Xcode 提供），即可在 Mac 上抓到 iPhone 全部流量（含局域网 UDP）：

```bash
# 1. iPhone 连 Mac 并点“信任”，查 UDID：
xcrun xctrace list devices
# 2. 用 UDID 建虚拟接口（替换 <UDID>）：
rvictl -s <UDID>
# 3. 开抓（需 root）：
sudo tcpdump -n -i rvi0 -X 'host 10.10.10.138 and udp port 8855'
# 4. 去 iPhone 点一个功能 → 终端里 EE… 开头即请求帧
# 5. 停止：Ctrl-C，然后 rvictl -x <UDID>
```

## 方法 B：在 UniFi 网关上抓（手机和灯跨 VLAN 时可用）

灯在 VLAN 10（IoT），若手机在别的 VLAN，流量会经 UDM 路由，可在网关 tcpdump：

```bash
# SSH 到 UDM 后
tcpdump -n -i any -X 'host 10.10.10.138 and udp port 8855'
```

`-X` 会直接打印 hex+ASCII；每条 `EE…` 开头的就是请求帧，`DD…` 是回包。
（若 `-i any` 不行，用面向该网段的桥接口，如 `br0`。手机和灯若在**同一 VLAN
且走交换机直连**，网关看不到这条流量，请改用方法 A。）

> **务必在网关(UDM, Linux)上跑，不要在 Mac/旁路主机上跑。** 交换网络里旁路主机
> 看不到手机→灯的点对点 UDP。在 macOS 上还会遇到 `ioctl(SIOCIFCREATE):
> Operation not permitted`——那是 `-i any` 要建 pktap 伪接口、需要 root；即便
> `sudo tcpdump -i en0 …` 能跑起来，Mac 不在流量路径上也抓不到。拓扑不确定时直接用方法 A。

## 要抓的动作清单（对应 roadmap）

| 功能 | 在 App 里的操作 | 对应待办 |
|------|----------------|---------|
| 时间同步 | 打开 App 连接灯的瞬间（自动发） | F5 |
| 闪电特效 | 底栏点「闪电」一次 | F6 |
| 云彩特效 | 底栏点「云彩」一次 | F7 |
| 自动云彩开关 | 「选项」里开/关「自动云彩」各一次 | F8 |
| 月相模式 | 「选项」里开/关「月相模式」各一次 | F9 |
| 适应模式 | 「选项」里开/关「适应模式」各一次 | F10 |
| 渐变时长 | 「选项」里把「渐变时长」滑到某值（记下分钟数） | F11 |
| 临开 | 底栏点「临开」一次 | F12 |

开关量（F8–F10）建议**开一次、关一次**各抓一条，方便我对比出哪个字节是开/关。
滑杆类（F11）**设成一个明确的值**（如 5 分钟）并告诉我那个值，方便对上编码。

## 给我什么

每个动作一行即可，例如：

```
闪电:  EE00....CC
云彩:  EE00....CC   （回包 DD00....CC）
月相开: EE00....CC
月相关: EE00....CC
渐变=5分钟: EE00....CC
```

我据此解码负载、实现对应实体/服务，并补上单元测试。

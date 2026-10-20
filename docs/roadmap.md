# Roadmap / TODO

Feature backlog for the Zetlight Horizon Aqua LED Home Assistant integration
(domain `zetlight_led`, developed on the M5-80M). This is the
authoritative task list; the protocol facts live in
[`m5-light-protocol.md`](m5-light-protocol.md).

Every item that isn't shipped yet follows the same loop:

> **capture → decode → implement → unit-test → release**

"Capture" means recording the real UDP frame the Horizon Aqua app sends while
you tap the corresponding control, so the exact payload can be confirmed before
any code sends it. Nothing is wired to a live device until its frame is verified.

## Status key

- ✅ **Shipped** — implemented, unit-tested against a captured frame, released.
- 🟢 **Ready** — command/format already known; implementable with no new capture.
- 🟡 **Needs capture** — command exists in the app (method name known), payload
  not yet decoded; one capture unblocks it.
- 🟠 **Needs decoding** — larger reverse-engineering effort (multi-field format).

## Backlog

| ID | Feature | App control | Command | Status | Next action |
|----|---------|-------------|---------|--------|-------------|
| F1 | On / off | 开关 | `0x1E` / `0x1F` | ✅ Shipped (v0.1.0) | — |
| F2 | Overall brightness | A–D sliders (live) | `0x13` | ✅ Shipped (v0.2.0) | — |
| F3 | Per-channel A/B/C/D | A–D sliders (live) | `0x13` | ✅ Shipped (v0.3.0) | — |
| F4 | Reachability / status read | — | `0x0C` | ✅ Shipped (v0.1.0) | — |
| F5 | Device clock sync | (auto in app) | `sendCurrentTimeAndDateCmd` | 🟡 Needs capture | Capture a time-sync frame; add a service/periodic sync |
| F6 | Lightning effect | 闪电 | `sendlightning` | 🟡 Needs capture | Capture the 闪电 tap; expose as a button/service |
| F7 | Cloud effect | 云彩 | `sendcloud` | 🟡 Needs capture | Capture the 云彩 tap; expose as a button/service |
| F8 | Auto-clouds toggle | 自动云彩 | config frame | 🟡 Needs capture | Capture toggling 自动云彩; expose as a switch |
| F9 | Moonlight mode | 月相模式 | config frame | 🟡 Needs capture | Capture toggling 月相模式; expose as a switch |
| F10 | Acclimation mode | 适应模式 | config frame | 🟡 Needs capture | Capture toggling 适应模式; expose as a switch |
| F11 | Fade/ramp duration | 渐变时长 (minutes) | config frame | 🟡 Needs capture | Capture setting the slider; expose as a number |
| F12 | Temporary-on timer | 临开 | timer frame | 🟡 Needs capture | Capture 临开; decide on entity shape |
| F13 | Read daily schedule | 5 time periods | `0x10` (read LED config) | 🟠 Needs decoding | Parse the `0x10` reply (times + per-period 4-channel setpoints) |
| F14 | Write daily schedule | edit/save periods | `sendSavelight` / `sendSaveFivelight` | 🟠 Needs decoding | Decode the save payload (timestamps + 4-channel values); apply + persist |
| F15 | Preset spectra (LPS/SPS #N) | 方案 presets | built on F14 | 🟠 Needs decoding | After F14, store presets in HA and write them to the device |
| F16 | Config-flow auto-discovery | — | broadcast `C9000000000A021D` | 🟢 Ready | Add a discovery step that broadcasts and lists responding beacons |

## Beyond the app (Home Assistant only)

These add value the vendor app can't, but still only use commands the device
supports:

- Automations/scenes: tie lighting to presence, time, sensors, or real weather
  (e.g. a storm scene triggering the lightning effect).
- A "feeding" / "maintenance" scene that dims channels, then restores them.
- Whole-tank scenes combining the light with the wave pump integration.
- Local history/logging of state via HA recorder.

## Known limitation

`0x13` (brightness / per-channel) is a **real-time preview**: it overrides the
live output but does not write the device's stored time-curve program. At the
next scheduled time point the device reverts to its program. Making changes
persist requires F14 (write schedule).

On/off and brightness states are **optimistic** — the device's read command
(`0x0C`) reports program setpoints, not live on/off state, so the integration
tracks the last command it sent.

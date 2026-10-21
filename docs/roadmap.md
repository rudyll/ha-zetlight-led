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
See [`capture-guide.md`](capture-guide.md) for how to capture the frames.

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
| F5 | Device clock sync | (auto in app) | `0x03` | ✅ Shipped (v0.5.0) | Button + auto-sync on setup |
| F6 | Lightning effect | 闪电 | custom `0x13` | ✅ Shipped (v0.5.0) | Custom white+blue flash (not the vendor effect); tunable |
| F7 | Cloud effect | 云彩 | `sendcloud` | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F8 | Auto-clouds toggle | 自动云彩 | config frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F9 | Moonlight mode | 月相模式 | config frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F10 | Acclimation mode | 适应模式 | config frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F11 | Fade/ramp duration | 渐变时长 (minutes) | `0x22` (observed) | ⏸️ Deprioritized | Frame partly decoded (see note); skip unless requested |
| F12 | Temporary-on timer | 临开 | timer frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F13 | Read daily schedule | 5 time periods | `0x10` | 🟢 Brightness decodable | Brightness at `0x10` offset 40 (20 B), raw-% bytes (confirmed). Could expose as a sensor. Time-slot bytes in the reply still unmapped |
| F14 | Write daily schedule | edit/save periods | `0x1C` + `0x11` | ⚗️ Experimental (v0.5.1) | Brightness **verified on hardware** (raw %, +START to apply). Times (`0x11`) still unverified — confirm before relying on the time part |
| F15 | Preset spectra (LPS/SPS #N) | 方案 presets | built on F14 | 🟠 Needs decoding | After F14, store presets in HA and write them to the device |
| F16 | Config-flow auto-discovery | — | broadcast `C9000000000A021D` | 🟢 Ready | Add a discovery step that broadcasts and lists responding beacons |

## Capture findings (2026-10-20)

A local capture (phone on the light's subnet, proxy off) while tapping several
mode controls was partly decoded. The effect/mode features (F6–F12) are
**deprioritized** — the user finds them low-value and unlikely to use. Recorded
here only so they don't need re-capturing if revisited:

- **渐变时长 (fade duration) — CMD `0x22`**, payload `[enable, minutes]`:
  - 5 min → `EE 00 08 01023A01 22 01 05 16 CC`
  - 3 min → `EE 00 08 01023A01 22 01 03 10 CC`
- Other command bytes seen from the phone during mode taps but **not reliably
  mapped to a feature** (the UI scrolled and several controls were tapped):
  `0x14` (payload `00 01 00` / `00 00 00`), `0x16` (`00 01 01`), `0x17`
  (`01 01 01` / `00 01 01`), `0x20` (no payload; reply carries a state page).
  These look like per-mode toggles/reads; re-capture one action at a time if
  ever needed.

The core local control the user actually wants (on/off + brightness + per-channel,
no cloud) is already shipped (F1–F4). The one remaining high-value item is the
daily schedule (F13/F14).

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

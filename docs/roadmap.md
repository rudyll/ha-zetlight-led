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
| F13 | Read daily schedule | 5 time periods | `0x10` | ✅ Shipped (v0.6.0) | `sensor.schedule` shows the 5×4 brightness (raw %); offset 40 assumes standard layout (may shift ±1 under some presets) |
| F14 | Write daily schedule | edit/save periods | `0x1C` + `0x11` | ✅ Verified (v0.6.0) | `set_schedule` service; **brightness (raw %) and times (BCD) both verified on hardware**, +START to apply |
| F15 | Schedule presets | named schedules | built on F14 | ✅ Shipped (v0.7.0) | `select.preset` applies named presets defined in the options flow (YAML) |
| F16 | Config-flow auto-discovery | — | broadcast `C9000000000A021D` | ✅ Shipped (v0.7.0) | Config flow broadcasts and lists responding lights; manual entry remains |

## Recovery follow-up (2026-10-24)

| ID | Source / authorization | Owner / priority | Scope / dependencies | State | Acceptance / evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| F17 | Rudy requested completing interrupted GTS/DualKey work, 2026-10-24 | Codex / P0 | Storm clear-weather recovery; existing GTS run-mode input | Software passed; installed and HA-expanded config verified | Seven transition cases; old condition fails clear/unavailable transitions and removal, revised condition passes. No live lightning or wave surge tested. | Current HA expansion includes the clear-weather condition and GTS tide selector. No real storm test. Public push separately authorized. |

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

Shipped (v0.8.0):

- ✅ **Feeding / maintenance mode** (`switch.feeding_mode`): dim + auto-restore.
- ✅ **Custom cloud effect** (`button.cloud`): ramp down, hold, ramp up.
- ✅ **Per-channel raw diagnostic sensors** (from `0x0C`).
- ✅ **Schedule overdrive** (values up to 200% in `set_schedule`).
- ✅ **Configurable scan interval** (options, 5–600 s).
- ✅ **Chinese (zh-Hans) translation** for the config/options flow.
- ✅ **Sun-anchored schedule blueprint** (sunrise/sunset).

Shipped (v0.9.0):

- ✅ **Acclimation mode** — `Acclimation` number scales the stored schedule's
  output non-destructively (snapshots a base, restores at 100%, persists until
  changed); the `acclimation_ramp` blueprint raises it daily.
- ✅ **Entity-name translations** (English + 简体中文).
- ✅ **Lightning-on-storm blueprint** — fire lightning from a HA weather entity.

Shipped (v0.10.0):

- ✅ **Whole-tank blueprints** (light + wave pump): feed, storm, day/night flow,
  maintenance — see `docs/blueprints.md`.

Still open / possible later:

- Local history/logging via HA recorder (works already; no code needed).
- Tailored pump defaults once the pump integration's entities are finalized.

Intentionally not done:

- **Native DHCP auto-discovery** — matching Espressif OUIs would false-match
  every ESP device on the network; the broadcast discovery (F16) covers setup.

## Known limitation

`0x13` (brightness / per-channel) is a **real-time preview**: it overrides the
live output but does not write the device's stored time-curve program. At the
next scheduled time point the device reverts to its program. Making changes
persist requires F14 (write schedule).

On/off and brightness states are **optimistic** — the device's read command
(`0x0C`) reports program setpoints, not live on/off state, so the integration
tracks the last command it sent.

# Changelog

## 0.11.0 — 2026-10-22

Blueprints: Chinese, repeating storms, and one-click import.

- **Storms now repeat with random timing.** `lightning_on_storm` fires lightning
  at a random interval the whole time the weather is stormy (not once). The new
  `whole_tank_storm` loops "lightning + a pump big-wave burst" then a calm gap,
  at random intervals, until the weather clears — all intervals/intensities are
  settable.
- **Bilingual blueprints:** every blueprint's name, description and field labels
  are now 中文 / English.
- **One-click import:** `docs/blueprints.md` has My-Home-Assistant import links
  for each blueprint, and explains that HACS installs the integration only —
  blueprints are imported separately.

## 0.10.1 — 2026-10-21

- **Whole-tank blueprints tailored to the GTS pump:** its control is a `fan`
  entity, so the blueprints now use `fan.turn_off` / `fan.set_percentage` (not a
  switch/number), plus the pump's wave-mode `select` for the storm surge. Entity
  pickers still keep them pump-agnostic.

## 0.10.0 — 2026-10-21

- **Whole-tank blueprints** (light + wave pump): coordinate the light with any
  wave-pump integration via entity pickers —
  - `whole_tank_feed` — pump pauses while the light's feeding mode is on.
  - `whole_tank_storm` — lightning + pump flow surge on stormy weather.
  - `whole_tank_day_night_flow` — day/night pump flow following sunrise/sunset.
  - `whole_tank_maintenance` — a toggle that stops the pump and sets full white.
- All blueprints are catalogued in `docs/blueprints.md`.

## 0.9.0 — 2026-10-21

- **Acclimation mode:** an `Acclimation` number (%) scales every schedule write,
  so you can ease new corals in. Pair it with the new acclimation-ramp blueprint
  to raise it a step each day and re-apply a preset.
- **Chinese entity names:** all entities now use translation keys, with English
  and 简体中文 names (the config/options flow was already translated).
- **Blueprints:** `acclimation_ramp.yaml` (daily ramp) and `lightning_on_storm.yaml`
  (fire the lightning effect when your weather entity reports a thunderstorm).
  Lightning itself is a manual `button.lightning`; triggering it from real
  weather/sun is done via these HA blueprints, since the integration has no
  weather data of its own.

## 0.8.0 — 2026-10-21

A batch of extras.

- **Feeding / maintenance mode** (`switch.feeding_mode`): dims all channels to a
  set level and auto-restores after a timer (configurable via `Feeding level` /
  `Feeding duration` numbers). Live-only; the stored program is untouched.
- **Cloud effect** (`button.cloud`): a custom passing-cloud dim-down → hold →
  ramp-up, built from live `0x13` frames, then restores the previous levels.
- **Per-channel raw sensors** (diagnostic, disabled by default): the device's
  internal per-channel drive values from the `0x0C` reply.
- **Schedule overdrive:** `set_schedule` now accepts channel values up to 200
  (the device supports >100%).
- **Scan interval option:** the status poll period is now configurable (5–600 s)
  in the integration's options.
- **Chinese (zh-Hans) translation** for the config/options flow.
- **Sun blueprint:** `blueprints/automation/zetlight_led/schedule_at_sun.yaml`
  applies a schedule whose start follows sunrise/sunset.
- DHCP auto-discovery is intentionally not added (it would false-match every
  Espressif device); the broadcast discovery from 0.7.0 covers setup.

## 0.7.0 — 2026-10-21

Adds discovery, schedule presets, and a ready-made dashboard.

- **Auto-discovery (F16):** the config flow broadcasts the discovery probe and
  lists responding lights to pick from; manual IP entry remains available.
- **Schedule presets (F15):** define named presets as YAML in the integration's
  options (**Configure**), then apply them one tap via `select.preset`. Each
  preset is a full daily schedule (start, 5 durations, 5×4 brightness).
- **Dashboard:** `dashboards/reef-light.yaml` — a dedicated dashboard (its own
  left-sidebar panel) with the light, channels, lightning, schedule and presets.

## 0.6.0 — 2026-10-21

Schedule read-out, and the schedule write is now fully verified.

- **Schedule sensor** (`sensor.schedule`): read-only view of the device's stored
  daily brightness curve (5 slots × 4 channels, raw %), decoded from the `0x10`
  reply and exposed in the sensor's attributes. (Offset assumes the standard
  layout; it can shift ±1 byte under some vendor presets.)
- **Schedule write (F14) verified on hardware.** Time slots (`0x11`) were
  confirmed too: the frame is stored verbatim and the app shows the written
  times correctly (BCD HH:MM). Together with the raw-% brightness fix in 0.5.1,
  `set_schedule` is no longer experimental.
- **More robust UDP reads:** replies are now matched by command byte, so the
  device's broadcast heartbeats (or a late ACK) can't be mistaken for a reply.

## 0.5.1 — 2026-10-21

Fixes the schedule brightness encoding after an on-device + app check.

- **Schedule brightness is raw percent, not BCD.** An on-device test (write
  `0x1C`, read back in the app) showed the stored byte equals the displayed %
  (`0x50` → 80%, `0x90` → 144%, …). `build_schedule_brightness` now writes raw
  bytes (`50% → 0x32`, `100% → 0x64`); values over 100 are allowed as overdrive.
  (The live `0x13` command still uses BCD — only the schedule differs.)
- The `set_schedule` service now also sends `START` (`0x1E`) after writing, since
  `0x1C` alone does not refresh live output (the app does save → start).
- Schedule time slots (`0x11`) remain unverified on hardware.

## 0.5.0 — 2026-10-21

Adds a custom lightning effect, clock sync, and daily-schedule writing.

- **Lightning** (`button.lightning`): a clean white+blue flash built from live
  `0x13` frames — no purple afterglow like the app's built-in effect — then
  restores the previous levels. Tunable via three config numbers: flashes (1–5),
  intensity (10–100%), flash duration (30–300 ms).
- **Clock sync** (`0x03`): a `Sync clock` button plus an automatic sync on
  setup, setting the device to Home Assistant's local time.
- **Write daily schedule** via the `zetlight_led.set_schedule` service (times
  `0x11` + brightness `0x1C`, 5 slots × 4 channels) — **experimental**. The
  write frames are confirmed accepted on hardware (the 20 brightness bytes land
  in the device's config), but the value→displayed-% mapping is not yet verified
  (the stored encoding looks preset/firmware-scaled). **This overwrites the
  device's stored program — test with values you can visually confirm.**
- **Read config** (`0x10`): a diagnostic `Read config` button logs the raw
  reply. Precise schedule parsing (F13) is still pending a safe write→read diff.
- Command formats were decoded from static analysis of the vendor app; see
  `docs/m5-light-protocol.md` §8 and `docs/roadmap.md`.

## 0.4.0 — 2026-10-20

**Breaking: the integration was renamed** from `zetlight_m5` to `zetlight_led`
to reflect that it targets Zetlight's Horizon Aqua LED lights generally, not
just the M5-80M.

- **Migration:** after updating, remove the old **Zetlight M5 Coral Light**
  entry/device and add the integration again as **Zetlight Horizon Aqua LED**.
  (The domain changed, so the old config entry can't be carried over.)
- Developed and verified on the M5-80M; other Zetlight LED models on the same
  local UDP protocol may also work (untested — reports welcome).
- Added a bilingual (English / 中文) README, a logo, a project roadmap
  (`docs/roadmap.md`), discovery keywords, and a GitHub Sponsors link.
- No functional change to on/off, brightness, or per-channel control.

## 0.3.0 — 2026-10-20

Adds **per-channel control**.

- Four new `number` entities — `Channel A`/`B`/`C`/`D` (0–100% sliders) —
  mapping to the app's per-channel sliders. Each change sends a full `0x13`
  frame with the other channels left at their current values.
- The overall-brightness light and the four channel sliders now share one
  channel state: the overall brightness follows the brightest channel, and
  setting it flattens all channels to the same level.
- Channel sliders are seeded from the device's reported setpoints on startup.
- Still a real-time preview (`0x13`); does not persist to the stored program.

## 0.2.0 — 2026-10-20

Adds **brightness** control.

- Overall brightness via the device-verified `0x13` command (four BCD channel
  values, `100 → 0xAA`, with both auxiliary bytes fixed at `0x00`). Home
  Assistant's 0–255 brightness is scaled to 0–100 and applied to all four
  channels together. Per-channel control is possible with the same frame but is
  not exposed in the UI.
- Note: `0x13` is a real-time preview and does not persist to the device's
  stored time-curve program. On/off (`0x1E`/`0x1F`) is unchanged.
- New unit tests assert the captured 10% and 100% dimming frames.

## 0.1.0 — 2026-10-20

First release. Local-LAN control of the Zetlight **M5-80M** coral light over
UDP (port 8855) — no vendor cloud, no Bluetooth.

**Features**
- `light` entity with **on/off** control using the device-verified commands
  `0x1E` (on/resume) and `0x1F` (off).
- Config flow: enter the light's IP; Home Assistant probes it (`0x0C`) and
  auto-detects the device code and name.
- `DataUpdateCoordinator` polls status every 30 s for reachability.
- Isolated, unit-tested protocol layer (frame build / XOR / parse) asserted
  against real captured frames.

**Known limitations**
- On/off state is **optimistic**: the device's read command only reports
  per-channel setpoints, not the actual on/off state, so Home Assistant tracks
  the last command it sent.
- **Brightness / per-channel dimming is not implemented yet** (`0x13`). The two
  auxiliary payload bytes (`i`/`i6`) still need one capture to confirm; the
  builder is a safe `NotImplementedError` skeleton until then.

**Installation**
Add this repository to HACS as a custom repository (category: *Integration*),
install, then restart Home Assistant and add the integration from
**Settings → Devices & Services**.

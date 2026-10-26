# Changelog

## 0.23.0 — 2026-10-26

- Add independent whole-tank weather v2 light and pump-gain profiles, a separate
  gain ceiling, missing-state handling, per-target failure isolation and recovery.
  Normal tidal gain is100%; adverse-weather examples add gain from the daily curve.
- Pump gain above100 requires GTS Wave Pump0.7.0 or newer with the matching entity
  range. Targets above the live entity maximum are skipped, not silently applied
  as stronger flow. Existing0.6.2 installs remain limited to100.
- Add a separate daily-baseline storm-gain blueprint: both phases use the original
  current-hour daily curve; gap gain never falls below weather gain. Enforce caps,
  off/night handling, persistent ownership and feeding/maintenance/restore guards.
  Requires GTS0.7.0 storm_gain, schedule/gain entities and explicit clock agreement.
  Legacy storm v2 keeps its absolute inputs; do not enable both for one pump.
  Defaults150/130%, raw cap80 are candidates, not measured tank safety limits.
- Include the unified feeding/maintenance v2 template and skimmer/return interlocks;
  name whole-tank templates generically to distinguish them from lamp-only ones.
- 102 tests and52 subtests passed. The new expanded storm template passed offline
  native HA validation; joint daytime/night simulations confirmed unchanged curves.
  This is software evidence, not physical flow, lightning or restoration acceptance.
- Upgrade: HACS integration updates do not replace imported blueprints or existing
  automation inputs. Reimport the desired template separately, preserve backups,
  confirm one writer per scaling entity, and keep candidates disabled until review.
  Install the paired GTS capability before enabling positive pump gain.
- Schedule-at-sun remains a full schedule writer: its durations and channel values
  replace the stored program. It does not merely shift the current curve. Do not
  enable its sample values over a tuned program without reviewing them.
- Automation saves may broadcast automation_reloaded and retrigger other listeners;
  inspect active delay/recovery workflows before editing. No live automation is
  enabled by this release, and no pump/light device update is performed here.

## 0.22.0 — 2026-10-24

- Persist the real feeding deadline and unfinished recovery across HA restarts;
  cancel timers on unload and retry failed recovery. Off, feeding, viewing,
  manual preview and schedule now share one explicit priority order.
- Prevent old cloud/lightning frames and cleanup from overriding newer user
  choices. Schedule writes no longer briefly resume an explicitly stopped lamp.
- Persist curve-write recovery state. Applying a new preset while dimmed rebases
  the overlay to that preset; 100% restores the new curve, including after restart.
  Require schedule-brightness readback before committing the new baseline.
- Refuse option edits when the existing options cannot be read; serialize sibling
  read/modify/write edits to preserve unrelated bits.
- Feed/maintenance templates reconcile on startup and restore each extra outlet
  independently before BLE recovery, so one BLE failure cannot skip power restore.
- `set_schedule` supports explicit `entry_ids`; installations with multiple lamps
  must select targets, avoiding accidental writes to every lamp.
- Upgrade: restart HA; reimport updated blueprints separately. Retry a failed
  preset before changing dimming. Device live brightness/on-off remains optimistic
  (UDP has no proven acknowledgement); brightness-curve readback does not verify
  stored schedule times. Hardware effects/outlet-cycle acceptance remains separate.


- Storm blueprint: admit the clear-weather replacement run in restart mode,
  so it actually restores the pump when leaving a storm (including weather
  becoming unavailable). Ignore unrelated calm-weather transitions.
- Add seven weather-transition regression cases.

- **`whole_tank_storm`: hand the pump back to its tidal schedule when the storm
  ends.** Setting a wave mode (surge/turbulence) puts the GTS pump into manual,
  so the old restore (wave mode + percentage) left it stuck in manual and dropped
  the tidal program. New optional "pump run-mode select" input; at storm end it is
  switched back to `tide` (configurable). Without it, the generic wave+percentage
  restore still applies.

## 0.21.0 — 2026-10-24

- **New "Resume schedule" button** (`button.*_resume_schedule` / 恢复日程): sends
  `START` (`0x1E`) to snap the light back onto its stored schedule for the current
  time — handy after a manual brightness change, or from an automation. (Turning
  the HA light off then on already does the same; this is a one-tap shortcut.)

## 0.20.0 — 2026-10-24

- **Effects now hand control back to the schedule when they end.** A live dim
  (`0x13`) is a *preview that holds* — it never expires on its own, so after an
  effect the device would stay stuck at that level and miss the schedule's next
  boundary (e.g. the nightly off — the light could be found still on in the
  morning). Lightning, cloud, and turning **feeding** or **viewing** mode off now
  send `START` (`0x1E`) to re-arm the stored program from the current time, so
  the light follows the preset again — including switching off if the current
  slot is an off/sleep period. Confirmed against the app's own "resume program"
  flow. (The HA sliders may briefly show the slot's configured level rather than
  0 during an off period; the device still physically turns off.)
- **Whole-tank blueprints are now open templates.** `whole_tank_feed`,
  `whole_tank_maintenance` and `whole_tank_storm` no longer force a wave pump —
  the `fan` pump is optional (storm with it empty = lightning-only). Feed and
  maintenance gain an optional, **multi-select, any-domain** "extra devices to
  power off" slot for gear that can only be cut at mains — a return pump, heater,
  etc. on a smart plug — switched off during the event and back on after
  (`homeassistant.turn_off/on`). Nothing is auto-matched by name; you pick every
  entity yourself, and can keep editing the automation as YAML after import.

## 0.19.0 — 2026-10-23

- **Better cloud effect, and a fade fix for cloud + feeding.** The custom cloud
  is now a realistic passing cloud — one or two clouds dim to a random depth with
  a smooth ease, hold, then clear. Crucially, the cloud and feeding effects now
  disable the device fade for their duration and restore it afterwards (a long
  gradient was otherwise smearing them, same issue lightning had).
- **Moonlight blueprint:** `moon_phase` sets a faint blue night light scaled by
  the real lunar phase (brighter near full moon), resuming the schedule in the
  morning. Subtle by nature — a natural touch, not a dramatic effect.

## 0.18.0 — 2026-10-23

- **Viewing / photo mode** (`switch.viewing_mode`): a white-balanced mix that is
  easy on the eye and the camera while corals still fluoresce — more white,
  moderate blue (keeps fluorescence), damped violet (the most camera-polluting).
  It snaps quickly (temporarily bypassing fade) and restores the previous levels
  when turned off. Tune the per-channel targets with the `Viewing A/B/C/D…`
  config numbers (default white-heavy).

## 0.17.0 — 2026-10-22

- **Fiercer, non-repeating lightning that beats the fade.** The culprit behind
  soft/regular flashes was the device's gradient/fade smoothing every change.
  Lightning now reads your fade setting, turns it off for the strike, and
  restores it exactly afterwards — so each bolt is sharp while smooth schedule
  transitions are kept. The bolt itself is a fierce, randomized storm (blinding
  main, hard multi-strikes, a machine-gun burst, an occasional sheet flash, and
  a random second wave) so repeats don't feel mechanical.
- **Fade control exposed:** `switch.fade` (on/off) and `number.fade_minutes`
  (decoded from the `0x22` command and the `0x20` reply), added to the dashboard.

## 0.16.0 — 2026-10-22

- **More dramatic, realistic lightning.** Each press is now a storm bolt: a brief
  dark dip for contrast, a full main stroke, then a few rapid flickers of varying
  intensity and random gaps, and a smooth afterglow that fades back to normal —
  instead of uniform even flashes with an abrupt restore. Still white+blue only
  (no purple), still tunable; default strokes raised to 3.

## 0.15.0 — 2026-10-22

**Broader model support.** The integration speaks the shared Horizon Aqua
protocol, not just the M5's, so other Zetlight lights should work:

- **Channel count is auto-detected** from the `0x0C` status reply (not hardcoded
  to 4), so 3-, 5-, 6-channel lights get the right number of channel sliders and
  raw sensors. Brightness, per-channel, lightning, cloud and feeding all adapt.
- **Setup uses each light's own device code** (discovery already reads it), so a
  non-M5 light connects with its real code instead of the M5's.
- Only the M5-80M is hardware-tested, and the daily schedule still assumes 5 time
  slots; other models welcome — please report issues.

## 0.14.0 — 2026-10-22

- **Auto-clouds and moon-phase switches** (decoded and verified on-device):
  `switch.auto_cloud` (random daytime cloud dimming, `0x14`) and
  `switch.moon_phase` (moonlight follows the lunar cycle at night, `0x19`).
  State is read from the `0x20` option reply.
- Dashboard gains a "Modes" card with the dimming, acclimation, clouds and moon
  controls.

## 0.13.1 — 2026-10-22

- **Whole-tank acclimation & weather dimming blueprints** (light + wave pump):
  drive both the light's Dimming and the GTS pump's Tidal intensity together —
  `whole_tank_acclimation` (daily ramp) and `whole_tank_weather_dimming` (by
  weather). The pump overlay needs tide mode (the acclimation blueprint sets it).

## 0.13.0 — 2026-10-22

- **Native coral-acclimation mode** (decoded from the app): `switch.coral_acclimation`
  toggles the device's own acclimation (`0x14`), and `sensor.acclimation_day`
  shows its day counter (1–10). Device-managed and non-destructive, but opaque
  (no percentage, and the exact ramp/completion isn't documented by the vendor).
- **Weather dimming:** the `weather_dimming` blueprint sets the dimmer from your
  weather entity (sunny → full, cloudy/rainy → dimmer), with a customizable
  percentage per condition. Great for tanks by a window.
- The `Acclimation` number is renamed **Dimming** (调光比例) — it is a general
  non-destructive output scale, used by both the weather-dimming and
  acclimation-ramp blueprints.

## 0.12.0 — 2026-10-22

**Acclimation reworked into a non-destructive global scale.** Previously it
scaled every schedule write, which overwrote your configured program. Now the
`Acclimation` number is a single percent that scales your existing schedule's
output while preserving its shape:

- The first time you lower it, your current schedule is snapshotted as the base
  and remembered; every change rescales from that base, and **100% restores the
  base** exactly.
- It is **persistent** — it stays until you change it; it does **not** auto-time
  out (that is feeding mode). Set up your normal full-brightness schedule first,
  then lower Acclimation to ease new corals in; the ramp blueprint raises it
  daily.
- The acclimation-ramp blueprint is simplified (just raises the number; no
  preset re-apply needed).
- Note: the wave pump already has a single global intensity (`fan.set_percentage`)
  and a `tide` run-mode, so it needs no per-channel/per-hour tweaking for the
  same effect.

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

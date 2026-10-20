# Changelog

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

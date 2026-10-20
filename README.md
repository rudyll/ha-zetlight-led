# Zetlight M5 Coral Light — Home Assistant integration

Local LAN control of the **Zetlight "M5-80M"** coral light (the one driven by
the *Horizon Aqua* app) over **UDP**, with no vendor cloud and no Bluetooth.

The integration talks directly to the light on your network:

```
Home Assistant  ──UDP :8855──►  M5-80M  (EE…CC request / DD…CC reply + XOR)
```

The full, device-verified protocol is documented in
[`docs/m5-light-protocol.md`](docs/m5-light-protocol.md).

## Status

| Feature | State |
| --- | --- |
| Turn on / off | ✅ Working (device-verified commands `0x1E` / `0x1F`) |
| Reachability polling | ✅ Reads device status (`0x0C`) every 30 s |
| Brightness / per-channel dimming | 🚧 **TODO** — scaffolding only |

### Why on/off is "optimistic"

The read-status command (`0x0C`) returns each channel's **setpoint**, which
does **not** change when the lamp is switched off. There's no field that
reliably reports the current on/off state, so the entity tracks the last
command it sent and assumes it took effect.

### Why brightness isn't done yet

Dimming uses command `0x13` with a payload of four BCD channel values wrapped by
two auxiliary bytes (`i`, `i6`) whose meaning isn't pinned down yet. The
builder exists as a `NotImplementedError` skeleton
([`protocol.build_set_light`](custom_components/zetlight_m5/protocol.py)) so it
can't send a malformed frame until one more capture confirms those bytes.

## Installation

Copy the integration into your Home Assistant config directory:

```
config/custom_components/zetlight_m5/
```

(so you end up with `config/custom_components/zetlight_m5/manifest.json`, etc.),
then restart Home Assistant.

## Configuration

1. **Settings → Devices & Services → Add Integration → "Zetlight M5 Coral Light"**.
2. Enter the light's **IP address** (port defaults to `8855`).

Home Assistant sends a read probe; a reply confirms the device is reachable and
auto-detects its device code and name.

> **Tip:** give the light a **DHCP reservation** in your router so its IP
> doesn't change. If Home Assistant and the light are on different VLANs, allow
> UDP to the light on port `8855`.

## Protocol source

Everything here is derived from static analysis of the Horizon Aqua app plus
read-only probing and switch tests against the author's own device. See
[`docs/m5-light-protocol.md`](docs/m5-light-protocol.md) for frame format, the
command table, and the raw captured frames the unit tests assert against.

## Development

```bash
pip install pytest
pytest tests/
```

The tests cover frame building and parsing against real captured frames
(`OFF = EE000601023A011F21CC`, `ON = EE000601023A011E20CC`, and a `0x0C`
status reply) and have no Home Assistant dependency.

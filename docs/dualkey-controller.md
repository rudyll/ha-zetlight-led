# Physical controller: M5Stack Chain DualKey → Home Assistant

Turn an [M5Stack Chain DualKey](https://docs.m5stack.com/en/products/sku/C147)
(ESP32-S3, 2 keys + 2 RGB LEDs) into a reef-tank controller + status light.
It joins Home Assistant over Wi-Fi via **ESPHome**, so all the logic lives in
HA and you can change it freely.

## Flash it

1. Install the [ESPHome add-on / dashboard](https://esphome.io) in HA (or the
   ESPHome CLI).
2. Create `secrets.yaml` with your `wifi_ssid` / `wifi_password`.
3. Add [`esphome/reef-dualkey.yaml`](../esphome/reef-dualkey.yaml), plug the
   DualKey in by **USB-C**, and install (first time over USB, then OTA).
4. It auto-discovers in **Settings → Devices & Services → ESPHome**.

Keep it on USB power for an always-on controller — Wi-Fi drains the 350 mAh
battery in hours. (Don't hold KEY1 while powering on: GPIO0 is a boot pin.)

## What it exposes

- **Button events** (automation triggers): `esphome.reef_key1_single`,
  `reef_key1_long`, `reef_key2_single`, `reef_key2_long`, `reef_both_long`
  (both keys held ~1.5 s). Raw `binary_sensor.key_1` / `key_2` are there too.
- **LEDs**: `light.status_leds` (both LEDs together, with **Pulse / Blink /
  Alternate** effects for alarms) and `light.key_1_led` / `light.key_2_led`
  (individual). Use the whole-strip light for alarm effects, or the per-key
  lights for per-key indication — not both at once.
- `sensor.battery_voltage`.

## Example Home Assistant automations

Swap the entity ids for yours. Suggested mapping: **KEY1 = feeding, KEY2 =
viewing, both held = maintenance** — all freely changeable.

```yaml
# KEY1 press -> feeding mode (light; the whole_tank_feed blueprint pauses the pump)
- alias: Reef key1 feeding
  triggers: [{ trigger: event, event_type: esphome.reef_key1_single }]
  actions:
    - action: switch.turn_on
      target: { entity_id: switch.aedc45_feeding_mode }

# KEY2 press -> viewing / photo mode
- alias: Reef key2 viewing
  triggers: [{ trigger: event, event_type: esphome.reef_key2_single }]
  actions:
    - action: switch.toggle
      target: { entity_id: switch.aedc45_viewing_mode }

# Both keys held -> maintenance (a helper the whole_tank_maintenance blueprint uses)
- alias: Reef maintenance
  triggers: [{ trigger: event, event_type: esphome.reef_both_long }]
  actions:
    - action: input_boolean.toggle
      target: { entity_id: input_boolean.reef_maintenance }
```

### Status LED by severity

Drive `light.status_leds` from your own condition. Here it follows an
`input_select.reef_status` with options `ok` / `warning` / `critical` / `severe`
(set that from your sensors — temperature out of range, a pump offline, ATO
low, etc.):

```yaml
- alias: Reef status LED
  triggers:
    - trigger: state
      entity_id: input_select.reef_status
  actions:
    - choose:
        - conditions: "{{ is_state('input_select.reef_status','ok') }}"
          sequence:
            - action: light.turn_on
              target: { entity_id: light.status_leds }
              data: { rgb_color: [0, 90, 20], brightness: 40, effect: "None" }
        - conditions: "{{ is_state('input_select.reef_status','warning') }}"
          sequence:
            - action: light.turn_on
              target: { entity_id: light.status_leds }
              data: { rgb_color: [255, 120, 0], brightness: 160, effect: "Pulse" }
        - conditions: "{{ is_state('input_select.reef_status','critical') }}"
          sequence:
            - action: light.turn_on
              target: { entity_id: light.status_leds }
              data: { rgb_color: [255, 0, 0], brightness: 220, effect: "None" }
        - conditions: "{{ is_state('input_select.reef_status','severe') }}"
          sequence:
            - action: light.turn_on
              target: { entity_id: light.status_leds }
              data: { rgb_color: [255, 0, 0], brightness: 255, effect: "Alternate" }
```

So: calm green when all is well, pulsing amber for a warning, solid red for a
problem, and the two LEDs flashing red in opposition ("Alternate") for a severe
alarm. You can also light `key_1_led` green/blue to show feeding is active, etc.

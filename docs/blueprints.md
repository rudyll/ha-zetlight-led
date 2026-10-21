# Blueprints

Ready-made Home Assistant automation blueprints in
[`blueprints/automation/zetlight_led/`](../blueprints/automation/zetlight_led).
Each takes entity pickers, so the whole-tank ones work with **any** wave-pump
integration (you select its switch / flow number at import).

To import: **Settings → Automations & scenes → Blueprints → Import blueprint**,
and paste the raw file URL (or copy the file into
`config/blueprints/automation/zetlight_led/`).

## Light only

- **schedule_at_sun** — write a daily schedule whose start follows sunrise/sunset.
- **acclimation_ramp** — each day raise the `Acclimation` % and re-apply a preset,
  to ease new corals in.
- **lightning_on_storm** — fire the lightning effect when your weather entity
  reports a thunderstorm.

## Whole-tank (light + wave pump)

These coordinate the light with a wave pump. They target the GTS pump
integration (`gts_wavepump`), whose on/off and intensity are a **`fan`** entity
(`fan.turn_off` / `fan.set_percentage`), with `select` entities for run-mode
(`tide` = built-in day/night curve) and wave-mode (`surge` / `turbulence` …).
You pick the entities at import, so other pumps with a `fan` entity work too.

- **whole_tank_feed** — when the light's Feeding mode turns on, pause the pump;
  resume it when feeding ends (one tap on the Feeding switch feeds the whole tank).
- **whole_tank_storm** — on stormy weather: lightning + surge the pump flow for a
  while, then return it to normal.
- **whole_tank_day_night_flow** — stronger "day" flow at sunrise, gentler "night"
  flow at sunset, following the light's rhythm.
- **whole_tank_maintenance** — a helper toggle that stops the pump and sets the
  light to full white for water changes; off restores both.

> Weather data comes from a HA weather integration (Met.no, etc.) — this
> integration has no weather of its own. The light's lightning/cloud are manual
> buttons; the blueprints are what tie them to weather, sun and the pump.

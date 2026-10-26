# Viewing brightness by sunrise / sunset

Source candidate, 2026-10-26. Blueprint: `viewing_sun.yaml`.
This is a profile selector, not an automatic all-night viewing schedule.
The requested distinction between those behaviours is awaiting owner confirmation.
No installation, enablement or actual light-output acceptance has occurred.

- Day: A/B/C/D = 10/10/30/25 by default. Night: 50% of day, rounded down,
  giving 5/5/15/12. Values are editable automation inputs, not measured PAR.
- Uses `sun.sun` above/below-horizon states, based on HA's configured home
  location. This does not shift, overwrite or save the lamp's stored schedule.
- The existing viewing button/switch still enters/exits viewing. If viewing is
  active across sunrise/sunset, its four viewing parameters change. If viewing
  is off, profiles preload locally using the existing viewing-number entities.
  No viewing-switch, light, pump or outlet service is called by the blueprint.
- Only select the same lamp's **viewing parameters**, never its live channel
  sliders. Actual candidate binding is verified against entity-registry unique
  IDs and device/config-entry identity; do not infer a function from its name.
- Feeding, maintenance or maintenance restoration prevent writes. Missing sun,
  missing mode/target data, non-finite values and duplicate targets stop the run.
  A powered-off lamp with viewing latched on is skipped, avoiding off/on commands.
  Guards are rechecked before each channel. Already matching values are skipped.
- Startup, sun transitions, viewing-mode changes, guard release, lamp-mode changes
  and target availability recovery reconcile the profile. No repeating timer.
- Four channel writes are sequential, not atomic or smoothly ramped. Failure
  stops remaining writes; completed channels are not rolled back. A later relevant
  trigger retries. This is not a guarantee against instantaneous external races.
- Turning this automation off leaves its last local viewing values in place.
  Restore previous viewing values explicitly if reverting. Exiting viewing still
  uses the integration's normal restoration; this blueprint adds no schedule write.

## Validation and installation boundary

14 focused tests / 31 subtests pass using the actual blueprint templates/actions:
day/night selection, non-compounding transitions, idempotence, unknown inputs,
duplicate targets, power-off and mode conflicts, feeding/maintenance interruptions,
and service failure. Native HA blueprint/automation schema checks and actual
registry-role/same-lamp binding checks pass in a synthetic local context. These
are not deployed-device acceptance. Full suite: 134 tests / 83 subtests PASS. Actual HA websocket read-only
validate_config confirms triggers and actions valid; no automation was saved or
executed. A normalized native config uses plural triggers/actions fields.

References: [HA sun](https://www.home-assistant.io/integrations/sun/),
[HA automation triggers](https://www.home-assistant.io/docs/automation/trigger/).

Before activation, confirm whether the owner wants button-controlled viewing with
automatic brightness (this candidate), or automatic viewing on/off at sunset/sunrise
(a different behaviour). Proposed installation needs no integration version bump
or HA restart. A global automation reload can retrigger existing pump/skimmer
protection: installation must use the established temporary guard-and-restore
procedure. That deployment and first profile application remain pending scoped
confirmation; do not silently replace the existing 90/50/60/25 viewing preset.
Private actual instance/baseline stay in ignored `.private/`.

## Latest: authorized whole-tank live recovery test completed — 2026-10-24

GTS-R02 linked Zetlight F18/F21: normal feed/end and GTS-unavailable outlet
recovery both passed. HA outlet history measures normal cuts11.67/11.82s and
fault-case cuts10.73/10.93s (water pump/skimmer). Earlier3.19/1.07s figures were
late polling windows and were explicitly corrected; raw evidence is retained.

Zetlight1min feed deadline survived actual entry reload unchanged and recovered
0.299s after the original deadline. Pumps were kept running during this lamp-only
phase by temporarily suspending the household power-control automation.
At12:29:06 all controls were restored: outlets on, GTS running tide/sine55, lamp
on/schedule, feed/view off, original10min duration and automation enabled.
No command/recovery flags. GTS/Zetlight/DualKey entries independently read loaded.
Guard exited without intervening; no scheduler/background observer remains.

User physical flow/skimmer/light appearance confirmation is pending. Control
acceptance is passed; that human observation layer remains open. No full Core
restart, real BLE-radio outage, actual thrown service error or generic maintenance
outlet deployment was tested. Do not expand the bounded acceptance claim.
Evidence and timing methodology: GTS repository
`docs/audits/2026-10-24-live-acceptance/README.md`. No runtime source change.
Next: user visual confirmation for GTS-R02 / normal model; no new test started.

## Current: authorized whole-tank live acceptance — 2026-10-24

Rudy explicitly authorized brief pump power cuts and requested final pump/light
restoration. Scope: normal feed/end; scoped GTS integration-unavailable recovery;
one-minute real lamp deadline across entry reload with the household feed
power-control automation temporarily suspended for that lamp-only phase.
Independent20s outlet-power guard plus120s stage recovery guard; original10min
feeding duration and automation enabled state must be restored. No full Core
restart, stored curve changes, storm flashes or broad network outage injection.
Physical flow/light appearance still requires user observation.
Executor: Codex; current GTS-R02, linked Zetlight F18/F21. Evidence goes into
existing ledgers after observed results; do not mark passed from script design.

## Publication verified — 2026-10-24

- [rudyll/ha-gts-wavepump 0.6.2](https://github.com/rudyll/ha-gts-wavepump/releases/tag/v0.6.2): remote manifest, annotated tag target, latest release, non-draft/non-prerelease status, and exact changelog notes verified. Release source commit `70a2dec2314f`.
- [rudyll/ha-zetlight-led 0.22.0](https://github.com/rudyll/ha-zetlight-led/releases/tag/v0.22.0): remote manifest, annotated tag target, latest release, non-draft/non-prerelease status, and exact changelog notes verified. Release source commit `6091a096c770`.
- DualKey source push completed; no binary or private configuration published.
- Subsequent commits only record verification evidence unless specifically noted below.

# Current audit repair status — 2026-10-24

## Runtime evidence added after deployment

HA native config check passed; the single requested restart completed. GTS,
Zetlight and ESPHome entries are loaded. New GTS native short test observed
feed/0 then running tide/sine/55; both original cuco outlets remained on. GTS
command_error is null and recovery_required false. Zetlight active_mode=schedule,
command_error null, no pending curve recovery; its actual light on/off remains
unknown because the device only reports program setpoints.

DualKey pairing completed through the official encrypted reconfigure flow.
New firmware's real unlock event arrived at 12:06:24 Asia/Shanghai; the real
key1-long at 12:06:27 matched the selected device and finished its empty action.
All six current event filters are scoped to that device. A proposed synthetic
live-event injection was rejected by automatic approval review; it was not run
or bypassed. Read-only native config validation and the user's real physical
sequence provided the safer verification path.

All local listeners exited; no persistent observation job was installed.
Physical abnormal combo timing, continuous WiFi/battery stability, battery ADC
calibration, actual status/alarm source and whole-tank outlet cycling remain
explicit acceptance/input gaps, not unimplemented audit fixes.

## Latest: F18–F22 audit fixes implemented; 0.22.0 deployment in progress

Persist feeding deadline and recovery obligation before hardware changes;
unload cancels callbacks, restart keeps the real deadline, failed recovery retries.
Serialize off > feeding > viewing > manual > schedule; effects are generation
checked and cannot resume an older intent. Low-level curve writes do not issue
START; coordinator applies the current intent after verification. Presets rebase
the current dimming baseline, with persisted partial-write state and brightness
readback. Saved dimming scale is authoritative after restart. Failed option reads
refuse writes; sibling read-modify-write operations are serialized. set_schedule
requires explicit entry_ids if multiple lamps are loaded.

Feed/maintenance templates reconcile current state on startup and restore extra
outlets independently before BLE recovery. The household's custom native-feed
automation retains its outlet targets and now follows the same recovery ordering.
Four installed blueprints passed HA native validation. 43 pytest tests and
9 subtests passed; tests simulate UDP/clock/store, not physical brightness.
The initial generic unittest runners lacked pytest or PyYAML; the combined
existing runtime passed the full suite. Runtime 0.22.0 is staged on HA and
`ha core check` passed; restarted Core loading and public release remain pending.

Known limits: live brightness/on-off remains optimistic UDP state. Curve
brightness readback does not verify stored schedule times. No new preset or
whole-tank storm was physically executed on the live tank. F17 storm transition
logic remains separately tested, with hardware acceptance open.
Next: observe loaded runtime, then release 0.22.0 / strong reasoning.

Rudy explicitly requested fixing all audit findings on 2026-10-24. Earlier
push/release authorization persists. Software tests simulate transport/storage;
they do not establish physical pump flow, LED colour, or outlet recovery.
No global scheduler or monitor was installed. The unrelated AquaTank checkout
was not changed. Runtime deployment was backed up under HA's
`/config/.reef-audit-fixes-20261024-115758`; blueprint/automation snapshots are in
`/config/.reef-blueprint-fixes-*`. Never blindly restore a whole automation file.

---


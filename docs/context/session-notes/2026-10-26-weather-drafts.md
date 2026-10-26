# F25: GitHub publication and disabled weather/storm drafts — 2026-10-26

## Requests and authority

Rudy asks for two concrete automations plus explanations of each setting, then
explicitly requests pushing new blueprints to GitHub. Prepared HA candidates OFF,
no device test/activation authority inferred. Public source publication authorized;
personal entity bindings remain ignored/private. Existing F24 source scope retained.

## Source and observed validation

F24 plus supporting unpushed feed/maintenance blueprint/docs/tests pushed normally
to origin/main4316369; ls-remote exact target and tracked source hashes checked.
No integration version bump, tag or HACS release. New storm_v2 adds persistent
ownership, feed/maintenance/restore/input availability guards, interruptible waits,
per-command checks, bounded parameters and owned tide restoration.11 new local
methods; complete suite90passed/38subtests. Both candidates' actual expanded
triggers/conditions/actions native validation passed, no execution in validation.
Display/source publication of storm_v2 follows this local commit; verify remote.

Weather v2 source/defaults unchanged. Seven independent draft profiles, pump
relative scale10..100; proposed normal80 vs actual read100 means adoption reduces
normal curve. Storm proposed65/45, ceiling65, burst8..12s, gap90..180s; fixed fan
setpoints do not track night curve and do not imply average flow is stronger.
Limits and night policy require user acceptance, not claimed safe from tests.

## Actual HA staging

Created two unique-ID candidates via config/automation/config with initial_state
false; both actual entities OFF, current0,last_triggerednull. Existing113 configs
semantically unchanged; no blanket reload, restart, synthetic event or device
service called by agent. Helper created OFF, weather source reused after canonical
comparison (HA added selector defaults/source_url); new storm source saved.
All11 protected state/last_changed values matched before/after. This is HA-state
proof, not optical/waterflow evidence. Personal bindings, private state receipts,
setting guide: ignored.private/weather-20261026; git check-ignore verified.
Raw working evidence /private/tmp/reef-weather-drafts-20261026 and HA private backup
/config/.reef-weather-drafts-20261026-112848. Earlier preflight backup attempts
preserved; ownership helper was created during an earlier stopped attempt.

## Observed edit side effect and correction

First stopped before saving while another anti-overflow automation was active.
Verified public exact2026.10.4 config API calls reload with only new automationID;
chose targeted saves. Missed the GLOBAL automation_reloaded event in same path.
The existing anti-overflow listener is mode:restart with15min delay. Saving drafts
emitted events: traces confirm03:28:55 and03:28:56UTC restarting that wait; previous
03:21 run cancelled. Latest restart11:28:56+08. Agent did not edit that automation.
Skimmer and return remainedON, unchanged since08:25:58+08; no outlet state change.
Do not claim the active task was entirely undisturbed because current stayed1.
User informed of missed listener/changed wait. No attempt to force timer restoration
or actuator recovery. Added concrete pre-save/global-event checklist to blueprints
runbook; future edits must check listeners and trace rather than current alone.
Docker inspection denied by existing protection; protection was not disabled.
Verified API behavior from official public sources instead, not container access:
https://github.com/home-assistant/core/blob/2026.10.4/homeassistant/components/config/automation.py
https://github.com/home-assistant/core/blob/2026.10.4/homeassistant/components/automation/__init__.py

## Handoff / remaining

Owns storm_v2/test, .gitignore.private, blueprint docs/progress/roadmap and this
note. Runtime integration/protocols/other automation source/credentials untouched.
No new monitor/background process. Candidates stay OFF across restart. Source
published is not a live storm or physical acceptance. Next F25-P01 PROPOSAL:
user reviews actual baseline, profiles, night policy and existing flash parameters;
then separate explicit enable/supervised test window, strong reasoning. No further
HA edit under this task after the observed reload-event effect.

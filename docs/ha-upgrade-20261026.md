# F29 / GTS-R13 HA upgrade verification — 2026-10-26

Verified at 2026-10-26T13:37:48+08:00 (Asia/Shanghai). DONE for the requested installation/blueprint
upgrade scope. No weather/storm activation or physical pump/lamp test was performed.
Personal entity bindings/raw snapshots remain in ignored.private/ha-upgrade-20261026.
This report/ledger follow-up is local documentation only; no new public release.

## Authorization and installed result

Rudy requests HA GTS/Zetlight and blueprint updates, weather/storm disabled, no
pump/lamp operation. Separately explicitly approves one HA restart and temporary
suspension/restoration of the feeding/maintenance controller and skimmer protection;
lamp startup clock sync was disclosed. That scope was used once.

- Native HACS update.install requested exact v0.7.0 and v0.23.0. All33component
  files matched the already-published tag bytes, and Python syntax passed.
- HA native structure validation passed for both migrated drafts. ha core check
  returned result ok before restart. No automation.reload/save API was used.
-14existing blueprint files updated in place from0.23.0, preserving source_url
  metadata. All14are visible to native blueprint/list without parse errors.
- Only the two already-OFF weather/storm draft YAML blocks changed.115total
  automations;113other definitions preserved, not reformatted/replaced. Weather
  draft uses positive daily-baseline gains; storm draft now selects the separate
  relative-gain template, clock_confirmed false. Both retain initial_state false,
  current0 and last_triggered null after restart and final readback.
- Only two idle control rules were temporarily disabled and given false startup
  guards for this restart. After HA RUNNING and loaded integrations were verified,
  the exact post-draft configuration file was restored and both rules re-enabled.
  Their last_triggered values did not change and current stayed0. Suspension
  duration241.9seconds. The two protected control rules did not execute.

## Runtime evidence

Actual loaded integration versions: GTS0.7.0, Zetlight0.23.0. Both config entries
loaded, GTS storm_gain registered and tidal gain maximum200. Gain value unchanged;
no gain service was called. HACS installed/latest versions nowv0.7.0/v0.23.0,
not in progress, with no restart-required summary. Source alone was not counted
as successful deployment.

Pump still reports on/tide. The two supply switches report on; mode/recovery/
owner helpers remain off. Lamp and pump stored schedule arrays compare equal
before/after restart. These are reported/configuration states, not physical flow
or illumination measurements. No pump/lamp on/off, brightness, feeding, storm,
curve-write or outlet-control service was called by this procedure. The explicitly
approved lamp startup clock synchronization is a separate startup side effect.

Lamp reports state unknown after restart with active_mode schedule, no command_error
and no pending curve recovery. The integration is optimistic and cannot read back
physical on/off; no turn_on was sent merely to make the UI say on. This remains
an explicit readback limitation, not a claim the lamp physically switched off.

## Restart and rollback evidence

Single restart request marked durably before sending. Its90second response timed
out; no second restart was issued. Read-only observation followed the same boot:
initial502, startup integration waits, then RUNNING and both entries loaded.
Logs also contained ZHA/Spook setup waits and an edge_tts platform error; those
components were not changed or diagnosed, and no causality is claimed here.

Verified rollback archive, original hashes, migration/guard copies and final
readback remain in HA's private release-backup folder. A checksum-verified local
archive is in /private/tmp/reef-ha-upgrade-20261026. Compact durable evidence and
current household draft guide are ignored.private/ha-upgrade-20261026; old private
weather guide is retained as superseded history. No credentials published, real
reef records/export changed, monitor created or unrelated automation enabled.

## Next boundary

F29/GTS-R13 DONE for software/runtime/blueprint upgrade. Weather/storm remain OFF;
physical clock agreement, intensity and failure-restoration acceptance are not
performed. Any enablement or device test needs separate scoped authorization and
a strong-reasoning model. Existing F27-A01 diagnostic label-width proposal remains
open, not fixed by installation. No further ready device action is authorized.

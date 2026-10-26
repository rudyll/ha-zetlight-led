# F28 paired release preflight — 2026-10-26

Software preflight complete; formal publication awaiting explicit authorization.
Prepared GTS0.7.0 and Zetlight0.23.0. No push/tag/Release/HA access or device action
performed by this preflight. No scheduled task or monitor created.

## Observed checks

- GTS71tests/41subtests PASS after improving storm command_error. Before the fix,
  two new/strengthened assertions failed on c8dfbcc. A failed/cancelled activation
  now distinguishes confirmed emergency stop/recovery required from stop unconfirmed.
  A failed preparation reports that mode switching was not attempted. Cleanup
  failure preserves the original exception/cancellation. Device stop implementation
  already requires heartbeat confirmation; this change exposes its outcome.
- Zetlight102tests/52subtests were observed passing in the preceding source task;
  custom_components/tests/blueprints are byte-for-byte unchanged from fe2e70f.
  No needless rerun claimed. New changes in this repository are documentation only.
- Native offline HA expanded config:9triggers/2actions PASS; captured GTS service
  registration/default schema PASS. Actual templates→fan method simulation PASS:
  baseline60 gives80/78 (cap80), baseline6 gives9/8; curves/baseline unchanged.
- Manifests0.7.0/0.23.0 match exact changelog/release bodies. Legacy absolute storm
  and weather blueprints preserved. Public GTS branch descends from publicmain;
  private acceptance commit5e530be is not an ancestor. No.private files tracked.
- Read-only remote checks via GitHub connector, gh and git ls-remote: official
  latest v0.6.2/v0.22.0, both non-draft/non-prerelease. Publicmain refs02a10798/
  c48589a5. Candidate tags v0.7.0/v0.23.0 absent. Initial sandbox CLI network access
  failed; scoped read-only escalation succeeded. No upstream movement observed.

Evidence: /private/tmp/storm-gain-20261026/release-preflight.json,
gts-preflight-tests.log and preflight-native-validation/service-schema/joint-validation.json.
Reviewable bodies: /private/tmp/reef-releases-20261026/gts-0.7.0.md and
zetlight-0.23.0.md; content is exactly each candidate changelog section.

## Upgrade and remaining gaps

Install paired GTS capability before enabling baseline-gain storm; importing a
blueprint alone cannot add storm_gain. HACS updates do not replace imported
blueprints or saved automation inputs. Legacy absolute storm v2 remains available,
so explicitly migrate to whole_tank_storm_gain and never run both for one pump.
No HA installation or activation is included in release authorization.

Pump-clock readback does not exist; clock agreement must be checked before enabling
this draft. Candidate gains150/130 and cap80 are not physically accepted settings.
Physical flow, lightning and failure restoration acceptance remain separate.
Known existing F27-A01 diagnostic issue: schedule sensor lists8labels even with
4values; listed in0.23.0 notes, no new channel mapping inferred for other models.
Fix proposal remains open; no controller/output change claimed. Schedule-at-sun
still replaces the full stored program and must not be described as time-only.

## Next authorized step

No further release mutation is authorized yet. F28/GTS-R11 requires an explicit
formal-publication decision. If approved, use only the public GTS worktree, push
final default-branch contents, tag that final commit and create non-draft/non-
prerelease releases with the reviewed notes, then verify remote manifest/tag/notes.
Do not push the primary GTS branch containing private raw history. Deployment,
HA reload/import, activation and supervised hardware acceptance need separate scope.
Next F28 publication decision, strong-reasoning model.

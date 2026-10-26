# F30-R01 Zetlight0.24.0 release and HA deployment receipt

Verified2026-10-26T14:35:11+08:00 (Asia/Shanghai). DONE for the explicitly authorized formal release,
HACS installation, guarded single restart and actual registry/readback scope.
No physical night-effect acceptance test or mode toggling was performed.

## Official release

[Zetlight0.24.0](https://github.com/rudyll/ha-zetlight-led/releases/tag/v0.24.0) published at2026-10-26T06:25:44Z, on final
commit3801a8ef43f89b39336ed200516411378903ae46. Final default-branch contents pushed before annotated
v0.24.0 tag and latest non-draft/non-prerelease Release. Remote main/tag manifests,
peeled tag target and exact changelog/Release notes match. Source tests remain
120passed/52subtests; source was unchanged from that observed result. This receipt
is a local follow-up and was not part of the tagged release content.

## HA deployment

- Fresh verified private backup includes previous component, registry, automations,
  blueprints and relevant recovery/HACS metadata. Local archive checksum verified.
- HACS native exact-version installv0.24.0 completed. All15component files match
  release-tag bytes, Python syntax and ha core check pass.
- Exactly one authorized restart. Its90second response timed out; subsequent502
  was treated as the same boot, never repeated. Readiness required actual new Lunar
  Phase registration in addition to RUNNING/loaded state, not a cached manifest.
- Two idle startup/reload control rules temporarily paused with false initial-state
  guards. After real runtime verification, exact config bytes and both original
  enabled states restored. Last-trigger/current unchanged; no rule executed.
  Suspension264.5seconds. GTS remains0.7.0; no GTS package/blueprint update.
- Real old entity_id/registry ID/unique ID/config entry/device/custom name retained;
  default translated name now月光开关. New distinct entity defaults to月相模式.
  No entity deletion/recreation or forced user-name migration.
- Read-only0x20before/after native option flags all equal; no native setter called.
  Independent Moon Light/phase entities match their separate returned fields.
  Lamp/pump stored schedule arrays unchanged; helper modes unchanged. HACS now
  installed/latestv0.24.0 without progress/restart-required summary.
- Weather/storm disabled, with no new trigger during this upgrade. Initial-state
  guards remain false. Baseline candidate-state drift was corrected according to
  the user's standing disable requirement; earlier trigger history was retained,
  not falsely described as never triggered. Details/real bindings remain private.

No pump/lamp on/off, brightness, feed, storm, curve-write or outlet-control service
used. Disclosed startup lamp clock sync is the approved exception. Lamp physical
on/off is not readable: unknown state/schedule intent remains a known limitation;
no turn_on was sent merely to change the UI state. No new scheduler/monitor/export.

## Evidence and next boundary

Raw compact receipt is ignored.private/moon-controls-deploy-20261026. Full HA
private rollback archive and /private/tmp/zetlight-024-release-20261026 contain
recorded hashes, baseline, install/check/restart/readback. This public-safe local
report intentionally omits actual entity IDs, flags and household bindings.

F30-R01 DONE; F30-P01 now deployed with actual identity acceptance. Hardware native
night-effect behavior and F30-P02 unused moonlight-blueprint channel assumptions
remain separate. No further live action is authorized. Next possible task requires
scoped approval, strong-reasoning model. This post-release receipt is local only.

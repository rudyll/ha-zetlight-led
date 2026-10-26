# F31-R01 / F31-A01 — 0.24.1 deployment and weather enablement

Verified 2026-10-26 16:01:39 +08:00. Formal publication, guarded upgrade and
actual HA label readback DONE. User separately authorized weather/storm control
and reported checking the pump clock in the vendor App against Beijing time.

- Official [v0.24.1](https://github.com/rudyll/ha-zetlight-led/releases/tag/v0.24.1)
  on final commit 7d82b9942dd62cb7d37329e6c46dccedcf8e0eba. Remote default/tag
  manifests, peeled tag, official latest release and exact notes all verified.
- HACS native install; all 15 component files match release bytes. Python syntax
  and HA core configuration check pass. Existing software result 120 tests and
  52 subtests passes; no executable changes beyond the previously verified work.
- One authorized HA restart. Response timed out and temporary 502 was observed;
  readiness required actual loaded entries and new Chinese label registration,
  not HACS's cached version. Runtime 0.24.1, GTS remains 0.7.0.
- All lamp registry identities and custom names preserved. All eight channel /
  viewing defaults read back as A白光, B UV紫光, C深蓝, D浅蓝.
- Two startup/reload guards paused 233.1 seconds and restored without execution.
  Original automation bytes restored at upgrade checkpoint. Native flags and
  stored pump/lamp schedules unchanged at that checkpoint. No mode, brightness,
  on/off, feeding, outlet or storm control command sent by deployment; startup
  lamp clock sync is the disclosed approved exception.
- Weather/storm were already on at baseline (both idle), then temporarily paused.
  Under the user's new explicit authorization, enablement changes exactly three
  fields: both persistent initial states to true and storm clock_confirmed to
  true. No unverified machine clock readback is claimed; confirmation is human.
- Automation reload emits a global event: protection rules were briefly guarded
  again (1.06 seconds), then their exact configured initial states and on states
  restored without new execution. Final all four rules on, no new weather/storm
  trigger during this transaction. No manual test trigger. Existing future
  weather/storm triggers are now authorized to control actual pump/lamp output.
- Blueprints unchanged in HA. No new monitoring task or scheduler. Lamp power
  remains reported unknown with schedule intent, not a physical illumination
  acceptance claim. Actual adverse-weather effects have not been tested here.

Raw evidence and personal lighting recommendation remain ignored under
.private/channel-labels-deploy-20261026; temporary full evidence is in
/private/tmp/zetlight-0241-release-20261026. Existing private HA backup retained.
Recommendations are AI proposals only, not actual settings or water-quality data.
Next: before coral introduction, species/placement and measured PAR should inform
spectrum/intensity selection; strong reasoning. No lighting recipe was installed.

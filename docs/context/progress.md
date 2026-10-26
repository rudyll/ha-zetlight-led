## Latest:0.24.0 formally released, HA upgraded, identity verified — 2026-10-26

F30-R01 DONE, readback2026-10-26T14:35:11+08:00. Official latestv0.24.0 on3801a8ef; remote main/tag
versions, tag target and exact release notes verified. HACS15files match tag,
syntax/native core check PASS. One approved guarded restart completed after
response timeout/initial502, no second restart. Actual new Lunar Phase registration
required before restoring guards. Runtime0.24.0 and HACS installed/latest confirmed.

Old entity ID/registry/UID/custom name preserved, default name月光开关; distinct
new月相模式 entity verified. Native0x20flags and pump/lamp curves unchanged; no
setter/toggle/brightness/feed/outlet command used. Startup clock sync was approved.
Two temporarily paused control rules restored without execution after264.5s; exact
automation file restored, blueprints unchanged. Weather/storm disabled; baseline
state drift corrected under the standing requirement, historical trigger retained.
No new trigger during upgrade; do not claim historically never triggered.

Safe report docs/zetlight-024-deployment-20261026.md. Actual IDs/options/backup and
drift details ignored.private/moon-controls-deploy-20261026 and private tmp evidence.
GTS unchanged0.7.0. Lamp unknown on/off/schedule intent remains readback limitation,
no physical night-effect test. No new monitor/export. Local receipt not pushed.
Next possible physical acceptance/F30-P02 proposal needs scoped authorization,
strong reasoning; no ready authorized live action remains.

---

## Latest: F30-R01 formal release + HA upgrade explicitly authorized — 2026-10-26

Rudy approves publishing0.24.0 and upgrading HA with previous guarded single
restart/two-controller pause-and-restore plan. Source120tests/52subtests and native
synthetic registry compatibility already verified; release/deployment now in
progress, not yet claimed complete. No mode toggles or pump/lamp action tests;
weather/storm remainOFF. Readonly actual registry/native options baseline is being
captured privately. No GTS/blueprint changes in this release. Next complete remote
publication then HACS/guarded runtime verification, strong reasoning.

---

## Latest: F30-P01 compatible moon controls implemented/tested — 2026-10-26

User authorizes label correction + independent native lunar switch with existing
entity compatibility. Local0.24.0 Unreleased candidate ready: old moon_phase UID/
translation key and0x19 code path preserved, default label Moonlight/月光开关;
new lunar_phase UID andphase0x14 control. Current option snapshot and shared lock
preserve sibling flags; returned options confirm target. Failed/cancelled action
leaves unknown options and raises; native phase/acclimation conflict refuses to
silently cancel either mode. No live HA/UDP/device access or setting changes.

120tests/52subtests PASS incl18new semantic cases. Native HA entity classes and
synthetic registry verify same old entity_id/registry entry/custom name and distinct
new entity. Legacy constructor/getter/on/off/client/frame AST unchanged. Source/
JSON syntax and candidate metadata valid. docs/moon-controls.md and0.24.0 Unreleased
notes explain compatibility and limits. Evidence private ignored and /private/tmp/
moon-controls-20261026. Code touched switch/client/coordinator, protocol comments,
translations, manifest, two tests and scoped docs; blueprints/GTS/real records/
HA configuration intentionally untouched. Existing physical deployment last verified
0.23.0 (F29) was not modified. No scheduler/background process, push/tag/Release.

Next proposed F30-R01: formal publication plus separately authorized HA installation
and registry readback, strong reasoning. Physical night effects remain untested;
F30-P02 unused moonlight-blueprint channel assumptions remains open. No further
live action authorized by this source task.

---

## Latest: F30 confirms moonlight mislabelled as lunar phase — 2026-10-26

Read-only investigation of Rudy's App/HA discrepancy: current HA Moon phase switch
reads options.moon/writes0x19, corresponding to App Moon Light. App Lunar Phase
is options.phase/0x14 second byte, not exposed separately. Android4.4.2 App callbacks
and builders independently confirm mapping;3focused protocol tests PASS. Label/
docstring error and missing separate control recorded; no implementation or HA/
device change. Report docs/moon-controls-audit-20261026.md, static source hashes
ignored.private/moon-controls-audit-20261026. Actual M5 effect not inferred; current
iOS UI not inspected. F29 installation remains complete, weather/storm disabled.
Next proposed F30-P01 backwards-compatible label + distinct lunar control correction,
strong reasoning, only if authorized. Unused moonlight blueprint channel assumptions
recorded as F30-P02 proposal, not installed/activated by this task.

---

## Latest: HA upgraded,14blueprints verified, weather/storm still OFF — 2026-10-26

F29/GTS-R13 DONE for installation/runtime upgrade, verified2026-10-26T13:37:48+08:00.
Native HACS installed GTS0.7.0/Zetlight0.23.0;33tagged component hashes and syntax
PASS, native draft validation/core check PASS. One explicitly authorized guarded
restart completed after a response timeout/initial502; no repeat restart. Loaded
entries, runtime versions/new storm service/max200 verified. HACS versions match,
no pending restart.14blueprints visible/error-free; only two OFF draft definitions
migrated,113other automations unchanged. Weather/storm remain OFF/current0/untriggered,
initial_state false; storm clock_confirmed false. Temporary two-rule guards/file
were restored exactly and rules re-enabled without execution (241.9s pause).

Pump reports on/tide and stored pump/lamp curves unchanged. Lamp reports unknown
on/off but schedule mode with no error/pending recovery; physical on/off was not
inferred and no turn_on issued. No pump/lamp/outlet control service or physical
test; disclosed/approved startup lamp clock sync only. Backup/raw bindings remain
private; compact durable evidence ignored.private/ha-upgrade-20261026 (Zetlight).
Safe report Zetlight docs/ha-upgrade-20261026.md. No public push/release, monitoring
or real-tank data/export change. These local documentation receipts are unpushed.

Next possible weather/storm enablement/supervised acceptance requires separate
scoped authorization (strong reasoning); no ready authorized device action.

---

## Latest: paired official releases published and verified — 2026-10-26

Rudy explicitly authorized publication. GTS0.7.0/v0.7.0 oncf199460 and Zetlight
0.23.0/v0.23.0 onca242cf1 are latest official non-draft/non-prerelease releases.
Remote tag/main manifests, annotated tag targets and exact changelog/Release notes
all verified. Tagged final contents were pushed BEFORE tags/Releases. Private GTS
acceptance history excluded; primary private branch never pushed.

F28/GTS-R11 DONE for publication. Safe receipt in Zetlight docs/release-publication-
20261026.md/.json; private raw verification in /private/tmp/reef-releases-20261026.
This post-publication documentation receipt is LOCAL ONLY, not pushed or tagged;
remote release contents remain the verified commits above. No source changed,
HA install/reload/import, automation activation, device action, export or monitor.
Physical flow/clock/failure acceptance remains open. Previous pending/in-progress
entries are historical and superseded by this observed completion.

Next possible HA upgrade/blueprint migration and supervised acceptance requires
separate scoped authorization (strong reasoning); no ready authorized device action.

---

## Latest: paired formal publication authorized and in progress — 2026-10-26

Rudy explicitly replies “可以” to publishing GTS0.7.0 and Zetlight0.23.0: push final
contents, create version tags and official GitHub/HACS releases. This does not
include HA installation/reload, blueprint import/activation or device actions.
F28/R11 publication is now authorized, superseding previous pending-approval
entries. Software preflight remains71GTS/102Zetlight tests,41/52subtests plus
native offline/joint validation; private acceptance history excluded. Remote
publication will only be marked complete after manifest/tag/Release/notes readback.
Next verify paired publication, strong reasoning; physical acceptance remains open.

---

## Latest: F28 preflight complete; publication decision pending — 2026-10-26

Release preflight found and fixed ambiguous storm failure telemetry: confirmed
stop/recovery versus stop unconfirmed. GTS71tests/41subtests PASS; Zetlight source
unchanged since102tests/52subtests PASS. Native offline config/service validation
and paired day/night actual-template→fan simulation PASS. Version/changelog/body
and private-history exclusion checks PASS. Read-only remote official versions
remain0.6.2/0.22.0, candidate tags absent. Known F27-A01 diagnostic width issue is
explicit in0.23.0 release notes, remains an open proposal. No publication/HA/
device action or monitor. See Zetlight docs/release-preflight-20261026.md.
Next F28/GTS-R11 explicit publication decision, strong reasoning; no further
consequential action inferred from “继续”. Earlier evidence remains historical.

---

## Latest: F27-C01 channel interpretation corrected — 2026-10-26

User confirms installed lamp channel meanings. Corrected ignored private lighting
context/analysis and preserved previous interpretation as superseded, without
changing raw samples, strengths, schedules or HA. No measured spectrum/wavelength
inferred and no Xiaochen handoff export/sync performed. Only task/progress receipt
is tracked; private user facts stay ignored. Next F28 publication decision, strong
reasoning; software completion and release boundary below remain unchanged.

---

## Latest: F26-P01 relative storm source/tests complete, release held — 2026-10-26

Rudy approves completing relative storm before formal publication. New additive
whole_tank_storm_gain blueprint requires GTS storm_gain and explicit pump/HA clock
agreement. Immutable daily baseline for both phases, gap >= current weather gain,
raw/gain caps, hour/off guards and owned tide restoration. Legacy storm_v2 unchanged.
70GTS/102Zetlight tests with41/52subtests pass; joint actual templates→fan method
simulations and offline native HA expanded-config validation pass. No HA connection,
config write/reload, device operation, activation, new monitor or publication.

GTS source belongs to public-isolated worktree /private/tmp/gts-weather-gain-public-20261026;
never push primary private acceptance history. Prepared0.7.0/0.23.0 changelogs and
release bodies now include this SOFTWARE scope. Physical flow/clock/night/restoration
acceptance and formal publication remain unapproved. See docs/storm-gain.md in
Zetlight for defaults/migration/limitations. Next F28/GTS-R11 paired release review,
strong reasoning; then separately authorized deployment/acceptance. Historical
notes below about unfinished F26-P01 are superseded by this entry for source only.

---

## Latest: version files prepared; current lamp analysis read-only — 2026-10-26

Version question: prepared GTS0.7.0/Zetlight0.23.0 manifests, matching changelogs and
reviewable release bodies.57/92tests PASS; official latest0.6.2/0.22.0 and no new
tags. Candidate not pushed/released; formal publication approval pending F28. No
HA edit/reload/device action. Imported blueprints need independent update; fixed
manual-storm relative gain remains unfinished F26-P01.

F27 sun/spectrum analysis: source schedule_at_sun writes COMPLETE times+brightness,
not a time-only shift. No matching active configuration found in current read.
Current user context, actual schedule and image analysis remain in ignored
private notes; no handoff export or real-tank data changed. Next F28 approval/publication and
F27 PAR-informed review, strong reasoning; no automatic device update authority.

---

## Current publication: paired gain source, no HA deployment — 2026-10-26

User explicitly authorizes GitHub update for the gain correction. Matching GTS
source and weather-blueprint candidate published as source only; no HACS version/
tag/release or HA edit. New source preserves normal100 and adds110..130 weather
gain, guards old max100 entities. Original manual-storm fixed65/45 remains an
open F26-P01 dependency before activation; neither existing HA draft is updated.

GTS public tree excludes unrelated private raw acceptance commits and passes
57tests/28subtests; weather source previously92tests/38subtests. Remote refs and
source hashes must match after push; record actual verification in task reply.
Next F26-P01 relative manual storm plus paired release/deployment proposal,
strong reasoning. No device operation authorized by GitHub publication.

---

## Latest: F26 corrects weather to positive daily-baseline gain — 2026-10-26

User clarifies daily tidal curve is already tuned; normal must100, bad weather
adds gain. Old80→100 plan superseded in design, retained in actualOFF drafts.
Local weather candidate100/100/100/110/115/120/130, ceiling130/max200, live entity
max guard prevents unsupported>100 writes on releasedGTS0.6.2. GTS-R10 counterpart
10–200/raw99 limit, immutable baseline/retry/restart/exact100 restoration; localonly.

57GTS tests/28subtests;92Zet tests/38subtests (one pytest-cache permission warning,
test run itself passed). Joint actual-template→fake-GTS five steps rain/wind/storm/
repeatstorm/clear preserve original20/40/60 fixture. Native trigger/condition/action
syntax valid. Readback confirms both HA draftsOFF,last_triggerednull. No HA edit,
config save/reload, device action, push, version/tag/release in this correction.
Next F26-P01 fixed65/45 manual storm must become baseline-relative before joint
activation; paired release/deployment remains unapproved, strong reasoning.
Private evidence /private/tmp/reef-weather-gain-20261026; existing.private guide
now flags the actualdraft policy superseded, candidate not installed.

---

## Latest: GitHub source pushed; two weather/storm drafts OFF — 2026-10-26

User requests concrete automations/tuning explanation and authorizes GitHub push.
F24/supporting source pushed main4316369 verified. New storm_v2 guards/ownership:
11newmethods, full90tests/38subtests, native configs valid. Both HA drafts created
OFF/current0/last_triggerednull; personal guide/bindings ignored.private/weather-20261026.
11protected states/last_changed unchanged; original113automation configs preserved.
No enable/device tests, integration release or monitor. Storm source push follows
this commit. [Full handoff](session-notes/2026-10-26-weather-drafts.md).

Correction: targeted save still broadcasts automation_reloaded. Missed anti-overflow
listener restarted its15min wait11:28:56+08; traces verified, skimmer/return both
stayedON. User informed; no timer/actuator override. Pre-save global-listener/trace
checklist added; no further HA edit this task. Do not claim active timer unchanged.
Next F25-P01 proposed baseline/profile/night/flash acceptance then separately
approved enable/test, strong reasoning. Candidates remainOFF; source tests not
physical acceptance, no HACS release claimed.

---

## Latest: F24 weather v2 source/tests complete; whole-tank names clarified — 2026-10-26

Rudy requests independent light/wave weather levels and brand-neutral whole-tank
names, with no real device actions. New opt-in weather_v2 has7 light/tidal profiles,
cap, missing-state skip, feed/maintenance/restore guards, manual-storm yield,
recovery triggers and branch isolation. Only two scaling-number targets, no power/
mode commands. Defaults are template proposals, not actual accepted settings.
Legacy weather input meanings retained;7existing names only changed to整缸联动 —,
semantic comparison7/7. New eighth source uses same prefix; live aliases unchanged.

19new tests; final fullsuite79passed/38subtests. HA read-only synthetic-trigger/
condition/action validation valid. No install/reload/device actions/push/release/
new scheduler. [Evidence and handoff](session-notes/2026-10-26-weather-v2.md).
Next F24-P01 proposed real baseline/cap/ownership review before separately approved
migration, strong reasoning. Separate manual-storm safety not certified by new
weather guards. DK-R11 and F23 device gates remain separate.

---

## Latest: F23 control coordinator enabled; physical acceptance pending — 2026-10-25

User requests enabling controls and confirms independent DualKey supply, unaffected
by skimmer switching. Actual HA blueprint substitution/validation passes. Legacy
feeding owner OFF, unified coordinator and DualKey mapping ON; persistent initial
states saved/read back. Before/after seven mode/actuator entities unchanged, no
synthetic events or real device tests. Controller unavailable11:29:57, recurring
DK-R11 fault remains; activation is not connectivity or physical acceptance.

Evidence/backup: HA private /config/.reef-controls-20261025; detailed source hashes
and boundaries in M5Stack docs/context/session-notes/2026-10-25-controls-activated.md.
No integration/source/firmware change, HA restart or new monitoring task. Next F23
physical acceptance requires online controller and separately authorized test;
DK-R11 diagnosis first, strong reasoning.

---

## Latest: F23 unified maintenance/native-feed control staged, not active — 2026-10-24

Rudy defines maintenance: stop wave and coral lamp, then skimmer before return;
heater not arrived/unbound. Confirms actual two supply roles and30s delay after
return starts before skimmer. Implemented opt-in whole_tank_modes_v2 with native
GTS feed preserved and one recovery owner. Mode/return rechecked after30s; no
skimmer if return is not confirmed on, no return cut if skimmer not confirmed off.
Unrelated stop failures continue; related failures stop with an HA trace error.
No water-level sensing or physical-flow guarantee is invented. Initially-off
lamp stays off via restore marker, user light commands cancel stale ownership.

17 real-template/action tests pass, including simultaneous modes/unknown inputs,
failed acknowledgement/partial targets/30s mode change and error recovery.
Actual HA blueprint substitution/schema validation passed; helpers created off,
coordinator/key staged OFF, existing feed owner remains ON. No device action test.
M5 source38 tests pass; strict mode-key cancellation/queued decisions implemented.
Successful firmware OTA is NOT a verified v2 runtime: actual controller remains
old16:43:40/no new effect; USB startup evidence unavailable at user request.

Only blueprint/tests/docs changed; no integration code/version/release or public
push, no consumer interface, scheduler, pump/lamp command. Next F23 enablement
per user control-first choice (single-owner handover) or wait DK-R10 USB resolution;
strong reasoning. Actuation acceptance stays separate. Authoritative state F23.

---

## Latest clarification: feeding and maintenance timing — 2026-10-24

User asked whether feeding/maintenance automatically restores operation. Live
Zetlight HA feeding duration10min; GTS native feed duration also10min. Key1 single
is whole-tank feed toggle; second single ends early. The whole-tank recovery
clock lives in HA and is persisted, not a timer running inside the lamp. During
Core downtime outlet recovery cannot execute until HA resumes. Maintenance
blueprint has no countdown, is manually ended and is not currently bound to
DualKey. Restore uses normal retained pump/current lamp program logic, rather
than an arbitrary snapshot of all manual brightness/power states.

Corrected feed description to remove the misleading lamp-internal-timer claim,
and maintenance description to explicitly say manual end/full brightness.
Installed metadata updated on HA; source comparison proved descriptions only,
and HA expanded triggers/actions matched unchanged source after normalizing
singular/plural keys. An initial whole-dict equality check failed; its pre-edit object was not saved,
so the exact initial difference is unproved. The description-only source check
and canonical native semantic comparison both passed. No aquarium
control actions, timeout settings or maintenance bindings were changed.

Optional maintenance timeout reminder is a proposal only; never automatically
restart pumps during water change without a separately defined/approved policy.
No new maintenance helper or scheduled reminder was created.

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

Rudy subsequently confirmed “看了都正常”. Control acceptance and the requested
user visual flow/skimmer/light restoration acceptance are passed for this test. No full Core
restart, real BLE-radio outage, actual thrown service error or generic maintenance
outlet deployment was tested. Do not expand the bounded acceptance claim.
Evidence and timing methodology: GTS repository
`docs/audits/2026-10-24-live-acceptance/README.md`. No runtime source change.
GTS-R02 is closed for this bounded acceptance. Latest user question concerns
DualKey status colour/effects and whether another LED ring is worthwhile;
that discussion is a design proposal, not permission to change live LED rules.

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


## F27 read-only sun/spectrum analysis outcome — 2026-10-26

Code proves schedule_at_sun overwrites full times+brightness; default900min15h
program is not a time-only shift. Read-only0x10 confirmed valid repeated BCD
boundaries and actual five-slot values; private evidence/analysis saved under
.private/lighting-review-20261026, no personal settings added to public docs.
Current species/PAR/LED wavelength uncertainty retained; no lamp/config action.
Next F27-P01 PAR/placement assessment if user supplies measurements, strong
reasoning. F27-A01 proposal: schedule sensor currently labels8channels despite
4values/row; do not interpret extra labels as physical channels. Solar target/
offset/time-preservation improvements are proposals, not implemented behavior.

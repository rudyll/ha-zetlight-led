# Roadmap / TODO

Feature backlog for the Zetlight Horizon Aqua LED Home Assistant integration
(domain `zetlight_led`, developed on the M5-80M). This is the
authoritative task list; the protocol facts live in
[`m5-light-protocol.md`](m5-light-protocol.md).

Every item that isn't shipped yet follows the same loop:

> **capture → decode → implement → unit-test → release**

"Capture" means recording the real UDP frame the Horizon Aqua app sends while
you tap the corresponding control, so the exact payload can be confirmed before
any code sends it. Nothing is wired to a live device until its frame is verified.
See [`capture-guide.md`](capture-guide.md) for how to capture the frames.

## Status key

- ✅ **Shipped** — implemented, unit-tested against a captured frame, released.
- 🟢 **Ready** — command/format already known; implementable with no new capture.
- 🟡 **Needs capture** — command exists in the app (method name known), payload
  not yet decoded; one capture unblocks it.
- 🟠 **Needs decoding** — larger reverse-engineering effort (multi-field format).

## Backlog

| ID | Feature | App control | Command | Status | Next action |
|----|---------|-------------|---------|--------|-------------|
| F1 | On / off | 开关 | `0x1E` / `0x1F` | ✅ Shipped (v0.1.0) | — |
| F2 | Overall brightness | A–D sliders (live) | `0x13` | ✅ Shipped (v0.2.0) | — |
| F3 | Per-channel A/B/C/D | A–D sliders (live) | `0x13` | ✅ Shipped (v0.3.0) | — |
| F4 | Reachability / status read | — | `0x0C` | ✅ Shipped (v0.1.0) | — |
| F5 | Device clock sync | (auto in app) | `0x03` | ✅ Shipped (v0.5.0) | Button + auto-sync on setup |
| F6 | Lightning effect | 闪电 | custom `0x13` | ✅ Shipped (v0.5.0) | Custom white+blue flash (not the vendor effect); tunable |
| F7 | Cloud effect | 云彩 | `sendcloud` | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F8 | Auto-clouds toggle | 自动云彩 | config frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F9 | Native Moon Light + Lunar Phase | 月光开关 / 月相模式 | `0x19` / `0x14` phase | Source/test complete,0.24.0 candidate (F30-P01) | Existing Moon Light identity retained; release/install/device acceptance separate |
| F10 | Acclimation mode | 适应模式 | config frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F11 | Fade/ramp duration | 渐变时长 (minutes) | `0x22` (observed) | ⏸️ Deprioritized | Frame partly decoded (see note); skip unless requested |
| F12 | Temporary-on timer | 临开 | timer frame | ⏸️ Deprioritized | Low value for the user; skip unless requested |
| F13 | Read daily schedule | 5 time periods | `0x10` | ✅ Shipped (v0.6.0) | `sensor.schedule` shows the 5×4 brightness (raw %); offset 40 assumes standard layout (may shift ±1 under some presets) |
| F14 | Write daily schedule | edit/save periods | `0x1C` + `0x11` | ✅ Verified (v0.6.0) | `set_schedule` service; **brightness (raw %) and times (BCD) both verified on hardware**, +START to apply |
| F15 | Schedule presets | named schedules | built on F14 | ✅ Shipped (v0.7.0) | `select.preset` applies named presets defined in the options flow (YAML) |
| F16 | Config-flow auto-discovery | — | broadcast `C9000000000A021D` | ✅ Shipped (v0.7.0) | Config flow broadcasts and lists responding lights; manual entry remains |

## Recovery follow-up (2026-10-24)

| ID | Source / authorization | Owner / priority | Scope / dependencies | State | Acceptance / evidence | Next action |
| --- | --- | --- | --- | --- | --- | --- |
| F17 | Rudy requested completing interrupted GTS/DualKey work, 2026-10-24 | Codex / P0 | Storm clear-weather recovery; existing GTS run-mode input | Software passed; installed and HA-expanded config verified | Seven transition cases; old condition fails clear/unavailable transitions and removal, revised condition passes. No live lightning or wave surge tested. | Current HA expansion includes the clear-weather condition and GTS tide selector. No real storm test. Public push separately authorized. |

## Capture findings (2026-10-20)

A local capture (phone on the light's subnet, proxy off) while tapping several
mode controls was partly decoded. The effect/mode features (F6–F12) are
**deprioritized** — the user finds them low-value and unlikely to use. Recorded
here only so they don't need re-capturing if revisited:

- **渐变时长 (fade duration) — CMD `0x22`**, payload `[enable, minutes]`:
  - 5 min → `EE 00 08 01023A01 22 01 05 16 CC`
  - 3 min → `EE 00 08 01023A01 22 01 03 10 CC`
- Other command bytes seen from the phone during mode taps but **not reliably
  mapped to a feature** (the UI scrolled and several controls were tapped):
  `0x14` (payload `00 01 00` / `00 00 00`), `0x16` (`00 01 01`), `0x17`
  (`01 01 01` / `00 01 01`), `0x20` (no payload; reply carries a state page).
  These look like per-mode toggles/reads; re-capture one action at a time if
  ever needed.

The core local control the user actually wants (on/off + brightness + per-channel,
no cloud) is already shipped (F1–F4). The one remaining high-value item is the
daily schedule (F13/F14).

## Beyond the app (Home Assistant only)

Shipped (v0.8.0):

- ✅ **Feeding / maintenance mode** (`switch.feeding_mode`): dim + auto-restore.
- ✅ **Custom cloud effect** (`button.cloud`): ramp down, hold, ramp up.
- ✅ **Per-channel raw diagnostic sensors** (from `0x0C`).
- ✅ **Schedule overdrive** (values up to 200% in `set_schedule`).
- ✅ **Configurable scan interval** (options, 5–600 s).
- ✅ **Chinese (zh-Hans) translation** for the config/options flow.
- ✅ **Sun-anchored schedule blueprint** (sunrise/sunset).

Shipped (v0.9.0):

- ✅ **Acclimation mode** — `Acclimation` number scales the stored schedule's
  output non-destructively (snapshots a base, restores at 100%, persists until
  changed); the `acclimation_ramp` blueprint raises it daily.
- ✅ **Entity-name translations** (English + 简体中文).
- ✅ **Lightning-on-storm blueprint** — fire lightning from a HA weather entity.

Shipped (v0.10.0):

- ✅ **Whole-tank blueprints** (light + wave pump): feed, storm, day/night flow,
  maintenance — see `docs/blueprints.md`.

Still open / possible later:

- Local history/logging via HA recorder (works already; no code needed).
- Tailored pump defaults once the pump integration's entities are finalized.

Intentionally not done:

- **Native DHCP auto-discovery** — matching Espressif OUIs would false-match
  every ESP device on the network; the broadcast discovery (F16) covers setup.

## Known limitation

`0x13` (brightness / per-channel) is a **real-time preview**: it overrides the
live output but does not write the device's stored time-curve program. At the
next scheduled time point the device reverts to its program. Making changes
persist requires F14 (write schedule).

On/off and brightness states are **optimistic** — the device's read command
(`0x0C`) reports program setpoints, not live on/off state, so the integration
tracks the last command it sent.

## Cross-integration audit — 2026-10-24

Rudy requested a read-only audit after authorizing publication. The following
were subsequently approved for implementation by Rudy: fix all problems. Evidence
and line references are in the GTS repository's
`docs/audits/2026-10-24-cross-integration-review.md`.

| ID | Priority | Finding / scope | State / success criteria | Next action |
| --- | --- | --- | --- | --- |
| F18 | P0 | A04 durable deadline/recovery; Rudy authorized live acceptance | Actual1min deadline unchanged across Zetlight entry reload; auto recovery0.299s after original deadline. Original10min restored | Rudy confirmed normal lighting after test; active-feed full Core restart not tested |
| F19 | P1 | A05 preset/dimming baseline; Rudy fix-all approval, Codex | Implemented/tested/deployed: new preset rebases immutable baseline, saved scale restores, partial write retained/readback required | Live destructive preset/failure injection not performed |
| F20 | P1 | A06 priority/generation ownership; Rudy fix-all approval, Codex | Implemented/tested/deployed: off > feed > view > manual > schedule; stale effects/cleanup cannot resume old intent | Physical cross-mode light acceptance remains separate; UDP output optimistic |
| F21 | P0 | A07 independent outlet recovery; Rudy authorized brief cuts | Household normal/end and GTS-unavailable end passed; actual outlet cuts max11.82s/10.93s; both outlets restored without guard | Rudy confirmed all normal; generic maintenance template remains native-validated, not physically instantiated here |
| F22 | P1 | A12 preserve unrelated option bits; Rudy fix-all approval, Codex | Implemented/tested/deployed: refuse failed reads, serialize sibling edits | Device transport remains unacknowledged UDP; no artificial failed-read live injection |

0.22.0 was pushed and formally released; remote manifest, tag6091a09, latest
non-draft/non-prerelease Release and matching notes were verified. F17's bounded storm condition
fix/installed configuration evidence does not close F18–F22 or certify all modes.

## Timing clarification / reminder proposal — 2026-10-24

- Current feeding:10min HA-managed persistent deadline; second Key1 single can
  end early. Current maintenance:manual helper off, no automatic countdown and
  no DualKey helper binding. Description-only corrections are installed; action
  semantics were verified unchanged.
- F23 (proposal, P2, owner unassigned): maintenance timeout reminder only; not
  authorized for implementation. Needs an actual maintenance helper, duration
  and notification destination. Success:notify without automatically restarting
  pumps. Next:wait for an explicit request; no reminder or scheduler created.

## Unified feeding/maintenance v2 — 2026-10-24

| ID | Priority | Source / scope | State / evidence | Next action |
| --- | --- | --- | --- | --- |
| F23 | P0 | Rudy requests maintenance stops wave/lamp/skimmer/return, confirms supply roles, specifies30s return-before-skimmer recovery and cancel-only keys; heater later | New opt-in whole_tank_modes_v2,17 actual-template tests and HA native validation pass; enabled on HA25Oct11:30 after explicit user request and independent-supply confirmation. Legacy feed OFF, key/coordinator ON. Native feed retained, maintenance wins, sequential acknowledgement guards, cancellation during settle and durable lamp restore marker. No physical actuation tested; controller currently offline11:29:57 | Configuration activation complete; persistent initial states and native validation verified. Supply coupling cleared by user confirmation, connectivity DK-R11 remains OPEN. Pump/light live acceptance requires available controller and separate authorization; strong reasoning |

## F24 — independent whole-tank weather rules (2026-10-26)

| ID | Source / authorization | Owner / priority | Scope and success criteria | State / next action |
| --- | --- | --- | --- | --- |
| F24 | Rudy requests independent lamp/pump weather rules, local implementation/tests only; explicitly no device operation | Codex / P1 | New opt-in weather v2: independent light/tidal percentages, windy/storm categories, bounded tidal baseline scaling; missing weather skipped; feeding/maintenance/restoration and manual storm ownership respected; recovery and independent failure paths tested | SOURCE/TEST COMPLETE:19 new methods, full79tests/38subtests; read-only HA synthetic trigger/condition/action validation passed.7existing whole-tank names brand-neutral, legacy actions/inputs unchanged. No deploy/device action/release/push; next F24-P01 proposal, strong reasoning |

### F24 acceptance boundary / F24-P01

New independent weather_v2 is opt-in; legacy retained. User naming clarification
applies to8source blueprints (7existing name-only,1new), not live automation aliases.
Evidence: docs/context/session-notes/2026-10-26-weather-v2.md.

F24-P01 PROPOSAL, Codex/P1: confirm real baseline/weather levels/caps, separate
manual-storm ownership/feeding-maintenance safety and a single scaling writer
before separately authorized migration. Depends on user's selected limits and
deployment authority. Source/tests complete; no live test/install approved.
Strong reasoning.

## F25 — published blueprints and disabled household drafts (2026-10-26)

| ID | Source / authority | Owner / order | State and evidence | Next action |
| --- | --- | --- | --- | --- |
| F25 | Rudy requests weather/storm automations and tuning explanation; explicitly authorizes GitHub push. Draft staging OFF, no device actuation | Codex / P1 | New storm_v2 ownership/mode guards,11newmethods; full90tests/38subtests, native expanded config valid. TwoHA drafts OFF/current0/untriggered, original113configs unchanged. F24 pushed main4316369, storm_v2 push follows this commit. Private guide ignored. No HACS release/live acceptance | F25-P01 profile/night/flash review then separately authorized enable/test, strong reasoning |
| F25-E01 | Observed side effect during draft saves | Codex / P1 corrected operating checklist | Targeted reload broadcasts global event; active anti-overflow listener15min wait restarted. Skimmer/return stayedON. User informed; no forced recovery, no further HA edit. Checklist added to docs/blueprints.md | Before future saves inspect global listeners/trace, not just reload target/current count |

F24-P01 draft-creation/source-publication scope now authorized and completed via
F25; real limits/physical activation remains proposal F25-P01, not silently closed.
Evidence: docs/context/session-notes/2026-10-26-weather-drafts.md.

## F26 — daily baseline plus positive weather gain (2026-10-26)

| ID | Source / authorization | Owner / priority | State and evidence | Next action |
| --- | --- | --- | --- | --- |
| F26 | Rudy corrects the model: existing daily curve is100, adverse weather adds gain; local implementation/testing only | Codex / P1, depends GTS-R10 | Local weather candidate normal100/rain110/wind115/pouring120/storm130, independent gain cap and live entity-max guard; GTS counterpart10–200 retains raw99 ceiling and immutable baseline.57GTS +92Zetlight tests pass; joint fake-transport5step sequence and native template validation pass. HA drafts remainOFF/untriggered; no HA edit/deploy/push/release | F26-P01 manual storm must also become baseline-relative; then coordinated review/release/deployment proposal, strong reasoning |

F25-P01's previous80..100 tidal profile is superseded as a design, preserved in
actual disabled HA drafts/history. Fixed65/45 storm draft is not final gain policy.
No activation authority inferred; prior GitHub push remains4570ae9, local gain
changes are unpublished until the paired capability/policy is ready.

### F26 GitHub source update authorized (2026-10-26)

Rudy explicitly requests GitHub updates too. Publish the matching GTS gain
source/tests and weather capability/default correction, without a HACS release
or HA/device change. GTS publication uses an isolated tree based on publicmain
to exclude unrelated local raw acceptance history. Source publication does not
close F26-P01 baseline-relative manual storm or enable either HA draft.

## F28 — versioned HACS release preparation (2026-10-26)

User asks why integration versions remain old. Prepared GTS0.7.0 and Zetlight
0.23.0 manifests plus matching changelogs/release bodies;57/92 tests respectively
PASS. Official releases remain0.6.2/0.22.0; intended new tags absent. Integration
release does not update imported blueprints/inputs. No release/tag/HA installation
or automation activation yet; formal publication approval pending. Fixed manual
storm relative gain remains F26-P01, not included as completed behavior. Owner
Codex/P1; next approval then default-branch push→tag→non-draft/non-prerelease release
and remote verification, strong reasoning.

## F27 — sun-event schedule semantics and lighting review (2026-10-26)

User requests analysis only. Code and read-only device config verified; sun
template replaces entire schedule, not merely start time. Current household
profile and user confirmations remain ignored.private/lighting-review-20261026.
No device operation or handoff export change. PAR/specific coral/wavelength data
limits retained. F27-P01 proposed PAR/placement assessment. F27-A01 proposed
sensor channel-label width correction, and future sun-template target/offset/
time-preservation design; no code fix claimed. Codex/P2, strong reasoning.

## F26-P01 — relative manual storm source closure (2026-10-26)

Source: Rudy asks to wait for storm-relative gain before release, then “做吧”.
Authorization: source/tests/local commit only; no HA/device change or release.
Owner Codex/P1, dependencies GTS-R10/R12. SOURCE/TEST COMPLETE: new additive
whole_tank_storm_gain plus GTS storm_gain; immutable baseline, gap weather floor,
raw/gain caps, original-hour timing, zero/off guard, owned restore and interlocks.
102tests/52subtests and paired GTS70/41 pass; offline native HA validation and
actual-template→fan-method daytime/night simulations pass. docs/storm-gain.md
records defaults, migration and unverified hardware/clock bounds. Old v2 unchanged.
This supersedes earlier unfinished source status, not physical acceptance.
F28 remains HELD pending explicit formal-release approval; prepared changelog and
matching release body updated. Next F28 release review (strong reasoning), then
separately approved installation and supervised acceptance; no automatic activation.

## F27-C01 — user-confirmed channel definition correction (2026-10-26)

Rudy supplies actual installed-lamp channel definitions. Codex/P2, documentation
correction only: DONE for ignored.private/lighting-review-20261026 context and
analysis. Prior inferred physical-channel labels superseded with traceable text;
historical sample values/time/raw read-config unchanged. No wavelength/irradiance
measurement inferred. No public integration labels, HA/device settings or personal
handoff export changed; no automatic Xiaochen sync claimed. Verification: JSON
parse, exact label readback and git-ignore check. Raw config was not written;
no before/after hash comparison was performed. Next F28 release decision (strong reasoning); new spectrum optimization
is not authorized or completed by a label confirmation.

### F28-P01 — final software preflight (2026-10-26)

Source “继续”; Codex/P1, prerequisite F26-P01. DONE for local software preflight,
publication still awaiting explicit approval. Fixed ambiguous GTS stop telemetry
with reproduced failing regression;71GTS tests/41subtests PASS. Zetlight102/52
evidence retained after exact source/test/blueprint equality check. Native offline
validation, joint simulation, version/body/private-history checks PASS. Report
docs/release-preflight-20261026.md. Known F27-A01 label-width issue remains proposal,
now included in candidate known limitations; no HA/device change or publication.
Next F28 formal release decision, strong reasoning.

### F28-R01 / GTS-R11 publication authorization — 2026-10-26

Source: Rudy explicitly says “可以” to formal paired publication of GTS0.7.0 and
Zetlight0.23.0. Codex/P1, dependencies F28-P01/R11-P01 complete. ACTIVE: authorize
final default-branch push, matching vtags and non-draft/non-prerelease GitHub
Releases with exact reviewed changelog notes, followed by remote verification.
Scope excludes HA installation/reload/import/activation and all device actions.
Use isolated public GTS tree, never primary private acceptance-history branch.
Success: remote versions/tags/final commit/official status/exact notes match.
Next complete and record actual remote readback, strong reasoning.

### F28-R01 / GTS-R11 formal publication closure — 2026-10-26

Rudy explicitly approved formal paired publication. Codex/P1; DONE for published
release scope. GTSv0.7.0(cf199460) and Zetlightv0.23.0(ca242cf1), both latest,
non-draft/non-prerelease. Remote manifest(tag/main), annotated tag targets and
exact changelog/Release bodies verified. Tagged final default-branch contents
pushed before tags/Release creation; private GTS acceptance history excluded.
Safe receipt in Zetlight docs/release-publication-20261026.md/.json; private
evidence /private/tmp/reef-releases-20261026/publication-verified.json. This ledger
closure is a LOCAL ONLY post-release receipt; do not confuse its commit with the
tagged code. Primary GTS private-history branch must never be pushed.
No HA installation/reload/import, activation, device action or monitor. Actual
local HACS UI refresh not checked. Next possible deployment/migration/physical
acceptance remains unapproved, strong reasoning; no automatic device work.

## F29 / GTS-R13 — paired HA upgrade, no device test (2026-10-26)

Source: Rudy explicitly requests HA GTS/Zetlight and blueprint upgrades, weather/
storm disabled and no actual pump/lamp operation. Subsequently explicitly approves
one HA restart and temporary suspension/restoration of the two startup/reload
controllers (feeding/maintenance and skimmer protection); lamp startup clock sync
is disclosed. Codex/P1; depends completed F28/R11 publication. ACTIVE: HACS native
specific-version downloads installed0.7.0/0.23.0;33tagged files exact hash/Python
syntax verified.14existing blueprints updated; only two OFF draft configs migrated
(weather baseline gains and relative storm, clock_confirmed false);113other
automations preserved. Native draft structure validation passed; core check and
single guarded restart/runtime validation pending. Private backup/evidence is
under /private/tmp/reef-ha-upgrade-20261026 and HA private release backup folder;
no raw bindings in public docs. Success requires loaded entry/new service/max200,
weather/storm still OFF/untriggered, helper modes unchanged, controllers restored
and no pump/lamp control service used. No publish/new monitor/hardware test.
Next complete one authorized guarded restart/readback, strong reasoning.

### F29 / GTS-R13 closure — 2026-10-26

Codex/P1. DONE for explicitly requested HA upgrade and blueprint migration.
HACS0.7.0/0.23.0 installed and runtime verified after one approved guarded restart.
33component hashes/syntax, native draft validation/core check PASS;14runtime
blueprints error-free. TwoOFFdrafts updated (relative storm with clock confirmation
false);113other definitions preserved. Both control rules restored without
execution after241.9s pause; helpers/gain/curves unchanged. Weather/storm
stillOFF/current0/nevertriggered. HACSno pending restart. Lamp on/off unknown is
explicit optimistic-state limitation; schedule/no error verified, no turn_on sent.
No pump/lamp/outlet service action or physical test; approved startup clock sync
only. Receipt Zetlight docs/ha-upgrade-20261026.md; actual bindings/backup/evidence
remain private/ignored. No monitor, export or new publication.
Next possible enablement/supervised acceptance is unapproved, strong reasoning.
F29-E01: startup edge_tts error observed, out of these integration domains;
diagnosis only a proposal for the kitchen-assistant owner, not a blocker/fix claim.

## F30 — native moon control meaning (2026-10-26)

Source Rudy asks why HA moon-phase switch differs from App. Codex/P1; read-only
analysis DONE. App4.4.2 decompilation and current integration agree: HA reads moon/
writes0x19 (Moon Light); App phase is separate0x14 second byte, parsed but not
exposed as a switch. Naming/semantic claim defect confirmed, no device change.
3focused protocol tests PASS,25deselected; docs/moon-controls-audit-20261026.md.
F30-P01 proposed correction: preserve existing UID/command, rename Moonlight and
add separate Lunar Phase control with unrelated-option preservation/semantic tests.
F30-P02 proposed audit of unused moonlight blueprint's assumed channel labels.
Physical M5 night effect and current iOS UI unverified. Next F30-P01 source fix if
authorized, strong reasoning; no automatic HA install/release/device test.

### F30-P01 — compatible Moonlight + Lunar Phase implementation (2026-10-26)

Source: Rudy explicitly asks to correct Moonlight name, add true Lunar Phase and
preserve existing entity compatibility. Codex/P1, depends completed F30 mapping
audit. SOURCE/TEST COMPLETE, local0.24.0 Unreleased candidate. Legacy moon_phase
UID/translation key, constructor/getter/actions/client/frame behavior retained;
display changed to Moonlight/月光开关. New lunar_phase UID reads phase/writes only
0x14phase, shared lock/readback confirms target and sibling fields. New failed/
cancelled action marks options unknown, no guessed success. Native phase and coral
acclimation conflicts require the other mode off, never silently cancel it.
120tests/52subtests PASS (18new semantic cases); native HA classes + synthetic
registry preserve old entity_id/registry ID/custom name and add a distinct entity.
Static AST equality confirms old Moon Light path unchanged. Historical test fixture
with both native modes enabled replaced by a valid independent-options fixture;
new negative/concurrent conflict cases cover the App's mutual exclusion explicitly.
Evidence ignored.private/moon-controls-audit-20261026/implementation-verified.json
and /private/tmp/moon-controls-20261026; guide docs/moon-controls.md.
Not published, installed, restarted, live-toggled or physically accepted; no HA/
device connection in this task. F30-P02 unused blue-light assumptions remains open.
F30-R01 proposed publication and separately approved HA install/registry readback,
strong reasoning; new physical-mode tests require their own scope.

### F30-R01 — official0.24.0 publication and guarded HA upgrade (2026-10-26)

Rudy explicitly authorizes formal0.24.0 publication and HA installation, using
the previous single-restart/two-controller pause-and-restore plan. Codex/P1;
depends F30-P01 complete. ACTIVE: final default-branch push→v0.24.0→official
Release/exact notes verification, HACS installation, backup/guarded single restart
and readonly actual registry/name/independent flags verification. No moon/phase/
feed/brightness/pump/outlet commands; startup lamp clock sync inherited from the
disclosed prior plan. Weather/storm stayOFF. No GTS upgrade or blueprint activation.
Success: release proven, runtime0.24.0, old ID/registry/custom name retained, new
phase entity independent, native option values/curves unchanged, rules restored.
Next complete authorized publication/deployment readback, strong reasoning.

### F30-R01 closure — official release and actual HA identity acceptance (2026-10-26)

Codex/P1; DONE for explicit publication/installation/restart/readback scope.
Official latestv0.24.0(3801a8ef), remote versions/tag/exact notes verified. HACS15
files exact, core check PASS; one authorized guarded restart, runtime0.24.0 and
actual new entity registered. Old entity ID/registry/UID/custom name preserved;
correctedMoonlight default plus separateLunar Phase default visible. Native flags/
stored curves unchanged, no mode/device control test. Paused rules restored without
execution (264.5s), exact automation bytes and blueprints unchanged. Weather/storm
state drift observed at baseline and corrected per standing OFF requirement;
historical trigger retained and no new trigger, not “never triggered”. Raw details
private. Report docs/zetlight-024-deployment-20261026.md. No new monitor/export.
F30-P01 deployed/identity-accepted; physical night effects NOT tested. F30-P02
remains an unused-blueprint proposal. No further ready authorized device work;
next scoped acceptance or proposal prioritization, strong reasoning.


### F31 — M5-M Chinese channel labels and source audit (2026-10-26)

Source: Rudy requests corrected channel names and official/third-party research;
then suggests cross-model consistency. Requested, Codex/P1, depends F30-R01 complete.
Implemented: channel/viewing A white, B UV violet, C royal blue, D ice blue; labels
follow owner-confirmed M5-80M mapping. Official M5-M diagram and retailer support
four groups/ranges, not universal A–D letter mapping. Evidence docs/channel-colours.md.
F30-P02 label-only scope addressed: optional moonlight inputs describe roles without
wrong B-blue hint; legacy keys/actions/bindings unchanged. Existing binding safety
and effect spectrum review remain proposed, not silently migrated or executed.
Success criteria: exact eight translation-name changes, valid JSON/YAML, unchanged
identities/defaults/actions, software checks; no live actions or publication.
DONE for source/research scope: 120 tests/52 subtests PASS; JSON/YAML and diff
checks PASS. Exactly eight translated names; number AST and blueprint actions,
keys/defaults/selectors unchanged. Additional lightning comments/docstring now say
A+B rather than white+blue/no-purple; executable AST unchanged. No HA access,
install/restart or output changes. System Python lacked pytest; successful full
run used existing /opt/miniconda3/bin/python.
Next release/install is pending explicit scope; strong reasoning.


### F31-R01 — publish/install corrected labels (2026-10-26)

Rudy says “做吧” to the stated publication/HA upgrade next step. Approved; Codex/P1.
Scope 0.24.1 formal release, HACS install and same guarded single HA restart with
two startup/reload controllers paused and restored. No output setting changes;
weather/storm remain off. Success: remote version/tag/release exact, installed
bytes/runtime labels verified, identities/configuration/curves preserved, controllers
restored without action. ACTIVE; next release then guarded deployment, strong reasoning.
Spectrum discussion is recommendation only, not authorization to write a schedule.


### F31-R01 closure / F31-A01 weather release authorization (2026-10-26)

F31-R01 DONE: v0.24.1 formal remote release verified, HACS15files exact, core
check pass; one guarded restart, runtime/new eight default names and all registry
identities/custom names verified. Stored curves/native flags unchanged at upgrade
checkpoint; 233.1s protector pause restored without execution. Report
 docs/zetlight-0241-deployment-20261026.md. Receipt is a local follow-up, not pushed.
F31-A01 source: explicit user approval to enable weather/storm actual control,
plus direct user confirmation of vendor-app pump clock matching Beijing. Approved,
Codex/P1, DONE: both initial states true, clock_confirmed true. Brief protected
reload1.06s; only three authorized config fields changed, four rules on, no new
protector/weather/storm execution during transaction. No forced weather test;
physical adverse-weather acceptance remains untested. Blueprint bytes unchanged.
Spectrum question answered as dated private AI proposal, not applied actual record.
Next proposed PAR/placement-based tuning before coral introduction, strong reasoning;
no further physical acceptance or schedule change authorized.

F31-D01 low-priority documentation follow-up: async_lightning method docstring
still says white+blue/no purple, unlike the corrected public description and
actual A+B implementation. Proposal, Codex, no output change or release authority;
next correct that remaining internal prose in a future source maintenance window.


### F32 — sun-based day/night viewing automation (2026-10-26)

Source: Rudy asks for viewing automation based on sunset, darker until sunrise.
Requested; Codex/P1. Scope being clarified: button-controlled viewing with automatic
profile selection (recommended) versus automatic on/off at sunset/sunrise. Existing
stored viewing mix is90/50/60/25, not the earlier AI suggestion. Candidate uses
10/10/30/25 by day,50% at night; no real profile or schedule was changed.
Implemented source blueprint + focused tests/docs, native schema/actual role binding
checks pass; software-tested candidate only. Four actual viewing targets verified
from registry unique IDs, same device/entry. Tests include unknowns, duplicate
inputs, interruption/failure, off-mode and idempotence. Full-suite result below.
Not installed, enabled, triggered, published or physically accepted; no HA output,
automation reload or scheduler. Success: selected semantics confirmed, profile
correct, guards/restoration preserved, then separately evidenced deployment.
Next resolve pending user choice, then scoped activation using guarded reload;
strong reasoning. No existing weather/storm or pump controller settings changed.


F32 software evidence: full134tests/83subtests PASS (14focused/31subtests);
native HA blueprint/expanded automation schemas pass and real HA readonly
validate_config reports triggers/actions valid. Actual candidate role/device bindings
verified; disabled private instance prepared, not saved to HA. No component code or
manifest changes, no push/tag/release. Business choice and scoped profile activation
remain pending; do not claim automation deployed. Next F32 user acceptance of
button-controlled profile semantics, day10/10/30/25/night50%, then guarded HA
blueprint install/reload/seed/readback; strong reasoning. Day/night percentages
are recommendations, not actual records or optical output measurements.


F32 activation authorization: Rudy replies “可以” to the concrete day10/10/30/25,
night50%, button entry/exit and guarded automation reload proposal, then separately
confirms profile-only semantics. Approved; Codex/P1 ACTIVE installation + preload
and runtime/readback. No integration restart, schedule write, pump/light-mode test,
GitHub push/release or automatic overnight viewing requested.


F32 closure — installed and runtime-verified 2026-10-26T17:33:20+08:00. DONE for approved profile-only
source/deployment scope: new rule enabled/persistent, current-day preset reads
10/10/30/25. Protected single reload paused two guards1.23s, both restored
without execution. New rule enabled and seeded only after guards restored; viewing
remained off/schedule intent unchanged. Stored pump/lamp curves, existing blueprint
and component bytes unchanged; existing rule configs preserved. Weather/storm on,
no new triggers during transaction. No HA restart, real mode switch, new monitor,
GitHub push/release. Report docs/viewing-sun-deployment-20261026.md; raw private.

F32-A01 — physical day/night/button acceptance gap. Proposal; owner Rudy observation,
Codex records; P2, depends deployed F32. Software134tests/83subtests and actual day
local-preset readback do not prove optical output or sunset/sunrise transition.
Success: observe ordinary viewing on/off by button and brighter day/dimmer night,
exit returns schedule. Not executed; no forced sun state or remote mode toggles.
Next record user observation when convenient, normal model. No further remote
physical test or publication is authorized. F31-D01 remains visible proposal.

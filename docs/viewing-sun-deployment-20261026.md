# F32 — viewing day/night automation installed

Verified 2026-10-26T17:33:20+08:00. User approved the concrete profile, button-controlled entry/exit
and temporary protected reload, then separately confirmed profile-only semantics.
DONE for installation, enablement and local-profile runtime verification.

- New approved blueprint and private actual instance installed, rule enabled and
  persistent initial_state true. Approved source SHA-256:
  `4a163f8b3cc327b805599873883d6166fabee69375c45e0f3c45e05a00b05d52`. No component/version change, HA restart or release.
- Day defaults A/B/C/D = 10/10/30/25. Night scale 50%, rounded down to5/5/15/12.
  Uses sun.sun from configured home location; no fixed wall-clock schedule added.
  Actual registry confirms four targets are viewing parameters on the same lamp.
- Existing feeding/maintenance and skimmer protection rules paused 1.23s with
  false initial-state guards during one global automation reload. Exact original
  rule settings restored; both on/idle with unchanged last-trigger timestamps.
- New rule stayed disabled throughout reload. After guards restored, it was enabled
  and triggered once solely to preload the approved current profile. Current sun
  above_horizon; all four viewing numbers read back10/10/30/25.
- Viewing switch remained off; lamp schedule intent unchanged. The integration's
  inactive-viewing path updates local parameters without sending brightness or
  on/off commands. No mode-toggle, pump/outlet or schedule-write action was called.
  Physical lamp power remains reported unknown; no optical claim is made.
- Stored lamp and pump schedules equal before/after. Existing blueprint bytes and
  installed component package unchanged. Only one new automation appended;
  existing automation entries semantically identical. Weather/storm remain enabled
  with no new trigger during this transaction.
- Before-file, registry, states and exact installed target backed up privately on HA;
  private local evidence in ignored.private/viewing-sun-20261026/deploy. No scheduler,
  monitor, integration upgrade or GitHub publication created by this task.

## Evidence limits / next step

Source134tests/83subtests and HA readonly structure validation already passed.
Deployed current-day preset application and rule readiness are verified. Actual
night transition, physical brightness and button-entry/exit acceptance have not
been exercised; no fake sun state or real mode change was used to manufacture
that evidence. F32-A01 retains this physical acceptance gap. Next normal-model
step is recording user observation during ordinary day/night viewing; no further
remote output test is authorized by this receipt.

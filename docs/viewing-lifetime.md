# F34 bounded viewing candidate — not installed

2026-10-26. Each newly enabled viewing session ends at the next verified lamp
schedule boundary or after30minutes, whichever comes first. Repeating enable and
day/night preset updates do not extend it. Expiry drops the old manual preview and
returns to the current native program, preserving feeding/off priorities.
Manual power-off cancels viewing and the deadline; explicit power-on resumes the
schedule, not an old viewing session. Viewing while manually off is refused.

The normal local UDP0x10 poll strictly parses only the verified M5 product code /
151-byte reply layout, time block20:40, local clock14:20. Calendar/BCD, repeated
boundary pairs and non-overlapping daily span are checked. Historical real frame
and an existing private read agree with the parser/recorded clock. No offset scan,
no guessed schedule from screenshots or brightness values. Unknown/stale(>90s)/
failed reads or clock skew>90s use only the30minute cap. A newly verified earlier
boundary may shorten a session; no refresh extends it. Sun-based viewing brightness
is a separate profile rule and is not interpreted as a lamp schedule boundary.

Deadline/start time persist in existing control storage. Restart after expiry,
invalid timestamps, clock rollback or legacy unbounded saved viewing drops viewing
safely; a live monotonic timeout still expires after wall-clock rollback. Startup
may therefore end an old viewing mode: this is a material upgrade behavior.
Feeding/manual-off expiry changes only the saved viewing intent without relighting
or sending another feed level. Failed recovery retries the current intent on its
own timer; it never ends a subsequently started feeding session. This scenario
was reproduced as a failing test before the fix. Stale/duplicate callbacks and
unload are covered. Missing time data remains null, not zero.

**Availability limit:** HA executes the return. If HA is down at the deadline,
physical live preview may continue until HA recovers; persistent startup handling
then reconciles it. This is not a hardware-independent30minute limit.

Existing entity IDs/unique IDs retained. Read-only schedule attributes now include
schedule_boundary_minutes and schedule_timing_read_at_unix; light adds
viewing_deadline_unix. No cloud preset service or schedule write is added.
Manifest remains the installed release number; changes are Unreleased source.

156tests/91subtests PASS, including captured/negative timing, persistence, midnight,
DST, clock rollback, storage/UDP failure, stale/duplicate callbacks and mode races.
Native HA coordinator/Store/timer and key blueprint validations pass in synthetic
local HA. Physical timing/brightness/keypress acceptance remains untested. No HA
configuration/device access, mode toggle or installation in this preparation task.
Future install must coordinate with M5Stack DK-R14 and preserve startup guards.

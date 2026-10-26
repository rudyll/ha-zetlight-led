# Relative storm gain (candidate, 2026-10-26)

Use `whole_tank_storm_gain.yaml` with GTS0.7.0. This is a new template; existing
`whole_tank_storm_v2.yaml` retains its absolute percentages for compatibility.
Never run both storm automations against one pump. Source tests do not establish
physical flow or safe settings for a particular tank.

## Calculation and defaults

100% means the original tuned daily curve. Both phases use that original baseline,
not the weather-scaled curve. Candidate peak150%, gap130%, gain ceiling160%, raw
power ceiling80 (protocol software maximum99). At base60 with weather130%, peak
is min(60×1.5,80)=80 and gap78. At night base6 gives9/8. Rounding and caps mean
these ratios are not physical water-flow ratios. Review these defaults before use.

Gap gain is max(configured gap,current weather gain). If current weather gain
exceeds the peak, or current weather output exceeds the raw cap, storm is skipped
and an owned manual storm returns to tide. It never weakens weather output just
to satisfy an inconsistent cap. Attenuation below100, pending overlay recovery,
missing baseline at non100 gain, invalid schedules and zero/off hours block entry.
Other hours may legitimately contain off slots.

The new GTS action reads current status/config, original overlay baseline and the
current HA local hour under the device operation lock. Config-v2 banks only.
It prepares bounded power and the day's period before changing waveform/manual
mode, then requires heartbeat confirmation. Failure after a possible output
change attempts a confirmed safe stop and reports command_error; this can stop
the pump and requires inspection/recovery. A failed command is not retried by
this blueprint and ownership remains visible. Daily curve and weather gain are
not rewritten by the transient action; manual banks retain the last setpoint.

## Time and modes

Pump time cannot currently be read back. The default-false clock confirmation
input must only be enabled after confirming pump time matches HA local time;
recheck after timezone/DST changes. No automatic clock synchronization is added.
The hourly trigger recalculates night/day output; ordinary schedule/gain/weather
changes also re-evaluate guards. Commands already in transit cannot be recalled.

Default peak waveform `daily` preserves that hour's waveform/period. Optional
surge/turbulence/pulse changes only the peak waveform; the gap uses daily. Burst
8–12s, gap90–180s; these are reviewable examples, not accepted device settings.

Feeding, maintenance and unfinished maintenance recovery take priority. Only a
running tide pump or this automation's owned manual session can be controlled.
No fan/light turn_on action is used. Lightning runs only for an already-on lamp
in schedule mode. User manual mode without ownership is left alone. A dedicated
persistent helper records ownership; restoration selects tide only when the
owned manual pump is running and interlocks permit it. Off/feeding/missing
states retain the marker until a later legitimate event. Already-tide sessions
can clear the marker without starting a pump in a zero slot. Disable/delete only
after checking restoration and the marker; do not manually erase ownership.

## Migration and evidence

New required selections: GTS tidal schedule sensor, GTS tidal gain number,
existing fan/run-mode/flow entities, dedicated owner helper and feed/maintenance
interlocks. Review the default-false clock confirmation and all limits. HACS
updates do not update imported blueprints. Released GTS0.6.2 lacks storm_gain;
importing this template there is insufficient. The legacy absolute v2 is retained.

Software evidence:70 GTS tests/41 subtests,102 Zetlight tests/52 subtests;
actual-template to actual fan-method simulations pass for daytime/night with no
curve rewrite. Offline native HA schema/trigger/action validation passes for the
expanded new blueprint. Hardware transport, clock agreement, physical flow,
lightning and real restoration under failures remain untested for this change.
No HA config was written or automation enabled, and no device was operated.

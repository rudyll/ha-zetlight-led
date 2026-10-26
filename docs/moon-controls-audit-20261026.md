# F30 moonlight / lunar-phase mapping audit — 2026-10-26

User asks what the HA moon-phase switch controls and why it differs from the App.
Read-only source/protocol investigation COMPLETE. A naming/coverage defect is
confirmed; no integration code, HA configuration or physical device was changed.

## Confirmed mapping

| Control | State field | Write | App callback |
| --- | --- | --- | --- |
| HA switch currently labelled Moon phase / 月相模式 | options.moon |0x19, one on/off byte | moonLightSwitch / sendMoonLightCmd |
| App Lunar Phase / 月相 | options.phase |0x14, second byte in auto_cloud/phase/coral payload | phaseModeSwitch / sendOption |

HA switch.py:120–140 reads opts.moon and calls async_set_moon. protocol.py defines
0x19 separately from0x14 and parses moon and phase into separate fields.
The existing Android4.4.2 app decompilation corroborates this independently:
LEDOptionActivity.java:411–438 changes phaseModeSwitch and sends options;
:457onward changes moonLightSwitch and sends the separate moonlight command;
:640–650 dispatches both through distinct methods. SendHttpOrUDPLEDXorByte.java
:1202–1260 and SendLEDAndAlgaeXorByte2.java:1115–1185 assign decimal25 and20.
Local source locations/hashes are retained privately, without publishing app code.

Thus the present HA control maps to the App's Moon Light control, not its Lunar
Phase control. The English/Chinese label and the switch docstring claiming lunar
cycle behavior are misleading. Existing parser separates phase, but no independent
phase switch or setter is currently exposed. Lack of synchronization with the
other App switch is not by itself evidence of UDP/WiFi failure.

This proves the command/UI mapping, not which LEDs the particular M5 firmware
uses, brightness, schedule interaction or physical night effects. Those remain
unmeasured; no switch test performed. The App version used for static evidence
is Android4.4.2, not a claim to inspect the current iOS UI.

General App-manual cross-check: Horizon Aqua manuals also distinguish Lunar Phase
from Moon Light. Related models' descriptions are not M5 effect/compatibility proof.
Manufacturer documentation entry: https://www.zetlight.com/horizon-aqua-app-40-a00017a1.html
Manufacturer-branded App manual copy: https://www.ipirangapeixes.com.br/manuais/zet/INSTRU%C3%87%C3%83O_APPP_HORIZON_AQUA_READY.pdf
PDF screenshot fetch failed in this run; no unseen screenshot details are claimed.
The command-mapping conclusion above rests on actual local App/integration source.

## Software evidence and limits

Observed command: PYTHONDONTWRITEBYTECODE=1 /opt/miniconda3/bin/python -m pytest
-q -p no:cacheprovider tests/test_protocol.py -k 'moon or options'.3passed,
25deselected. Frame tests confirm encoded command and distinct parsed fields;
they did not catch incorrect semantic labels. Fix acceptance needs explicit
UI-to-command semantic tests in addition to byte checks.

A separate moon_phase.yaml automation simulates moonlight using HA moon sensor,
time triggers and channel values. It does not invoke the native switch. It was
absent from the actual HA blueprint list captured during F29. Its generic color
labels assume channelB is blue; channel assignments are model-specific and must
not be treated as verified for every lamp. Do not infer installation/activation
or a safe physical moonlight intensity from this source template.

## Proposed correction, not implemented

F30-P01: retain the existing entity unique ID and its0x19 behavior for backward
compatibility, correct its displayed name/descriptions to Moonlight / 月光开关,
and add a distinct Lunar Phase entity/setter for options.phase. Preserve unrelated
option bytes and define how to handle the App's acclimation/phase interaction;
do not silently repurpose existing automations to a different command. Add
semantic separation and preservation tests. Needs scoped source/fix approval;
installation/publication/hardware acceptance remain separate.

F30-P02: revise the unused moonlight blueprint's assumed channel-color labels and
selection/guard policy before recommending it. No actual household bindings or
light levels are published here. Proposal only, no automatic implementation.

Next F30-P01 source correction if authorized, strong-reasoning model. No device
work authorized by the user's question.

# Native moon controls (0.24.0)

| Display name | Identity | Device control |
| --- | --- | --- |
| Moonlight / 月光开关 | Existing `<entry_id>_moon_phase`, retained |0x19 Moon Light, reads options.moon |
| Lunar phase / 月相模式 | New `<entry_id>_lunar_phase` |0x14 second byte, reads options.phase |

The old display name confused two different App controls. Renaming corrects the
label; it does not repurpose the old entity or migrate existing automations to a
different native feature. Its entity_id may still contain moon_phase. Keep it.
A user-set name is preserved rather than forcibly renamed. Fresh installations
may derive a default entity_id from the new name; existing registry entries keep
their identity because the platform/domain/unique ID remain unchanged.

Lunar Phase reads current options, modifies only phase, writes and confirms the
returned phase/cloud/acclimation fields under the shared option lock. Read errors
send no guessed packet. A failed/cancelled command or unconfirmed readback marks
options unknown and raises the error; it does not silently replay or undo a device
command. Subsequent normal polling can read actual state again. Moon Light still
uses its existing0x19 command, independent of the phase flag.

The native App makes lunar phase and coral acclimation mutually exclusive. Here,
first turn off the other native mode before enabling one. The integration refuses
the conflict instead of resetting a running acclimation cycle or silently changing
the other switch. Turning a mode off preserves the other native flags/day value.
This does not refer to HA feeding, which is a separate coordinator feature.

Adding/setup of these entities does not turn either feature on. This source change
does not install/enable the separate moon_phase.yaml automation. Channel assignments
and actual nocturnal output cannot be inferred from the option name; hardware
night-effect testing is separate. The App source mapping was checked against the
existing Android4.4.2 decompilation, not a new physical/iOS acceptance test.

Verification:120tests/52subtests,18new cases, plus offline native HA entity class/
registry check. Old registry entry ID/entity_id and custom name remain unchanged;
new lunar entity is distinct. No live HA connection, release, restart, switch
action, pump/light operation or firmware installation occurred in this task.
Deployment/physical acceptance still requires separate authorization.

"""Frame building and parsing for the Zetlight M5 local UDP protocol.

Pure protocol layer with no Home Assistant dependencies so it can be unit
tested in isolation. See ``docs/m5-light-protocol.md`` for the full, device-
verified protocol description.

Frame layout (old "EE/DD" protocol with XOR checksum)::

    request:   EE 00 LEN <device code 4B> CMD <payload...> XOR CC
    response:  DD 00 LEN <device code 4B> CMD <data...>    XOR CC

* request header ``0xEE``, response header ``0xDD``, trailer ``0xCC``
* ``LEN`` is a single length byte preceded by a ``0x00`` high byte; it counts
  the bytes from the device code up to and including the XOR byte
  (device 4 + cmd 1 + payload N + xor 1 = 6 + N).
* ``XOR`` is the running XOR over ``[00 LEN <device> CMD <payload>]`` — i.e.
  everything from frame index 1 up to (but excluding) the XOR byte itself.
"""

from __future__ import annotations

from dataclasses import dataclass

REQUEST_HEADER = 0xEE
RESPONSE_HEADER = 0xDD
TRAILER = 0xCC

# Device product code for this lamp (M5-80M). Carried back verbatim in read
# replies, so it can be confirmed / auto-discovered from a 0x0C response.
DEFAULT_DEVICE_CODE = bytes.fromhex("01023A01")

# Command bytes (subset of SendLEDAndAlgaeXorByte2 that we actually use).
CMD_READ_STATUS = 0x0C   # read live lighting status (read-only)
CMD_READ_CONFIG = 0x10   # read LED config incl. schedule (read-only)
CMD_SET_LIGHT = 0x13     # set per-channel brightness (live preview)
CMD_SYNC_TIME = 0x03     # set device clock (BCD yy mm dd hh mm ss)
CMD_SAVE_TIMES = 0x11    # save the 5 time-slot boundaries
CMD_SAVE_SCHEDULE = 0x1C # save the 5-slot x 4-channel brightness curve
CMD_SET_OPTIONS = 0x14   # set option switches [auto_cloud, phase, coral]
CMD_SET_MOON = 0x19      # set native Moon Light on/off (1 byte)
CMD_SET_FADE = 0x22      # set gradient/fade time: [enable, minutes]
CMD_START = 0x1E         # turn on / resume (device-verified)
CMD_OFF = 0x1F           # turn off (device-verified)
CMD_READ_OPTIONS = 0x20  # read option/mode state

NUM_SLOTS = 5  # the device's daily schedule has 5 time slots

# In a 0x20 option-state reply, the switch bytes start at this frame offset:
# [auto_cloud, phase, coral, moon]. The coral byte is 0 (off) or 1-10 (the
# acclimation day while running). Device-verified 2026-10-22.
OPTIONS_OFFSET = 14
# Fade (gradient) enable/minutes live further along the same 0x20 reply.
FADE_ENABLE_OFFSET = 23
FADE_MINUTES_OFFSET = 24

# New-protocol discovery probe broadcast to :8855; devices answer with a
# ``DD...CC`` beacon that carries their device code and name.
DISCOVERY_FRAME = bytes.fromhex("C9000000000A021D")
CMD_BEACON = 0x01  # discovery beacon reply command

NUM_CHANNELS = 4


def _xor(data: bytes) -> int:
    """Return the running XOR of ``data`` as defined by the protocol."""
    x = 0
    for b in data:
        x ^= b
    return x & 0xFF


def build_frame(cmd: int, payload: bytes = b"", *, device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build a request frame for ``cmd`` with an optional ``payload``."""
    if len(device_code) != 4:
        raise ValueError("device_code must be exactly 4 bytes")
    # LEN counts device + cmd + payload + the XOR byte.
    length = len(device_code) + 1 + len(payload) + 1
    if length > 0xFF:
        raise ValueError("payload too long")
    middle = bytes([0x00, length]) + device_code + bytes([cmd]) + payload
    return bytes([REQUEST_HEADER]) + middle + bytes([_xor(middle)]) + bytes([TRAILER])


# Convenience builders for the verified on/off commands. Both take no payload.
def build_off(device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build the OFF frame (CMD 0x1F)."""
    return build_frame(CMD_OFF, device_code=device_code)


def build_on(device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build the ON / resume frame (CMD 0x1E, START)."""
    return build_frame(CMD_START, device_code=device_code)


def build_read_status(device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build the read-status frame (CMD 0x0C)."""
    return build_frame(CMD_READ_STATUS, device_code=device_code)


def _to_bcd(value: int) -> int:
    """Encode a 0-100 brightness as the device's BCD byte (100 -> 0xAA)."""
    if not 0 <= value <= 100:
        raise ValueError("brightness value must be 0-100")
    if value == 100:
        return 0xAA
    return ((value // 10) << 4) | (value % 10)


# The two auxiliary payload bytes around the four channel values are fixed at
# 0x00 (device-verified, see docs §6b).
SET_LIGHT_PREFIX = 0x00
SET_LIGHT_SUFFIX = 0x00


def channel_limit(device_code: bytes = DEFAULT_DEVICE_CODE) -> int:
    """Verified overclockable marine M5: raw percent0..200; other models retain100."""
    return 200 if device_code == DEFAULT_DEVICE_CODE else 100


def build_brightness(
    channels: tuple[int, int, int, int],
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build live0x13 preview. Verified marine M5 uses raw0..200, NOT BCD.

    Other device codes keep legacy BCD0..100 until their encoding is verified.
    Accepted historical BCD-shaped frames prove transport acceptance only, not
    their claimed displayed percentages. This does not save the lamp schedule.
    """
    if not channels:
        raise ValueError("need at least one channel value")
    limit = channel_limit(device_code)
    if any(type(c) is not int or not 0 <= c <= limit for c in channels):
        raise ValueError(f"channel value must be an integer0..{limit}")
    payload = (
        bytes([SET_LIGHT_PREFIX])
        + bytes(channels if device_code == DEFAULT_DEVICE_CODE else (_to_bcd(c) for c in channels))
        + bytes([SET_LIGHT_SUFFIX])
    )
    return build_frame(CMD_SET_LIGHT, payload, device_code=device_code)


def _bcd(value: int) -> int:
    """Plain BCD for a 0-99 value (no 100->0xAA special case)."""
    if not 0 <= value <= 99:
        raise ValueError("BCD value must be 0-99")
    return ((value // 10) << 4) | (value % 10)


def build_read_config(device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build the read-config frame (CMD 0x10). Reply carries the schedule."""
    return build_frame(CMD_READ_CONFIG, device_code=device_code)


def build_time_sync(
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    second: int,
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build the clock-sync frame (CMD 0x03).

    Payload is 6 BCD bytes ``yy mm dd hh mm ss`` (year is the last two digits),
    matching the app's ``sendCurrentTimeAndDateCmd`` (year passed as ``y-2000``).
    """
    payload = bytes(
        _bcd(v) for v in (year % 100, month, day, hour, minute, second)
    )
    return build_frame(CMD_SYNC_TIME, payload, device_code=device_code)


def build_schedule_brightness(
    slots: list[tuple[int, int, int, int]],
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build the save-schedule-brightness frame (CMD 0x1C).

    ``slots`` is the daily curve: ``NUM_SLOTS`` tuples of four channel values,
    laid out ``slot0:A B C D, slot1:A B C D, ...``. Each channel byte is the
    **raw percentage** (device-verified 2026-10-21): the stored byte equals the
    displayed % (e.g. 50 -> 0x32, 100 -> 0x64). Values above 100 are allowed as
    overdrive (the app shows them in red), the verified marine M5 limit is200. Other model codes remain limited to100.

    The verified marine M5 also uses raw percent for live0x13; legacy models
    retain their BCD live encoding.

    WARNING: this overwrites the device's stored brightness program.
    """
    if len(slots) != NUM_SLOTS:
        raise ValueError(f"expected {NUM_SLOTS} slots")
    payload = bytearray()
    for slot in slots:
        if len(slot) != NUM_CHANNELS:
            raise ValueError(f"each slot needs {NUM_CHANNELS} channel values")
        for c in slot:
            if type(c) is not int or not 0 <= c <= channel_limit(device_code):
                raise ValueError("schedule channel exceeds verified model range")
        payload += bytes(slot)
    return build_frame(CMD_SAVE_SCHEDULE, bytes(payload), device_code=device_code)


def build_schedule_times(
    start_minute: int,
    durations: list[int],
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build the save-time-slots frame (CMD 0x11).

    ``start_minute`` is the first slot's start (minutes from midnight) and
    ``durations`` the length of each of the ``NUM_SLOTS`` slots in minutes.
    Payload is BCD ``HH,MM`` pairs: start, then each cumulative boundary — the
    first four boundaries written twice, the last once — exactly as the app's
    ``sendtimerange`` does (each boundary wraps at 1440).

    WARNING: this overwrites the device's stored time program.
    """
    if len(durations) != NUM_SLOTS:
        raise ValueError(f"expected {NUM_SLOTS} durations")

    def hm(minutes: int) -> bytes:
        minutes %= 1440
        return bytes([_bcd(minutes // 60), _bcd(minutes % 60)])

    payload = bytearray(hm(start_minute))
    boundary = start_minute
    for idx, dur in enumerate(durations):
        boundary = (boundary + dur) % 1440
        # first four boundaries are written twice, the last one once
        payload += hm(boundary) * (1 if idx == NUM_SLOTS - 1 else 2)
    return build_frame(CMD_SAVE_TIMES, bytes(payload), device_code=device_code)


@dataclass(frozen=True)
class DeviceStatus:
    """Parsed payload of a 0x0C read-status reply."""

    device_code: bytes
    name: str
    # Per-channel setpoint brightness (the configured level, NOT on/off state).
    setpoints: tuple[int, ...]
    # Per-channel raw / power values.
    raw: tuple[int, ...]


def parse_frame(frame: bytes) -> tuple[bytes, int, bytes]:
    """Validate a ``DD...CC`` reply and return (device_code, cmd, payload).

    Raises ``ValueError`` if the header/trailer/length/XOR do not check out.
    """
    if len(frame) < 9:
        raise ValueError("frame too short")
    if frame[0] != RESPONSE_HEADER:
        raise ValueError(f"unexpected header 0x{frame[0]:02X}")
    if frame[-1] != TRAILER:
        raise ValueError(f"unexpected trailer 0x{frame[-1]:02X}")
    length = frame[2]
    # middle is everything the XOR covers: [00 LEN device cmd payload]
    middle = frame[1:-2]
    xor = frame[-2]
    if _xor(middle) != xor:
        raise ValueError("XOR checksum mismatch")
    # length counts device + cmd + payload + xor; verify against actual frame.
    if length != len(frame) - 4:  # minus EE, 00, LEN, CC
        raise ValueError(f"length byte {length} does not match frame")
    device_code = frame[3:7]
    cmd = frame[7]
    payload = frame[8:-2]
    return device_code, cmd, payload


# In a 0x10 config reply the 20 schedule-brightness bytes start at this frame
# offset (after DD 00 LEN code 10 <name6> <date/time...>), device-verified.
SCHEDULE_OFFSET = 40


@dataclass(frozen=True)
class ScheduleTiming:
    """Verified standard M5 local-wall-clock timing, not an inferred preset."""

    boundaries: tuple[int, ...]
    clock_fields: tuple[int, ...]


def parse_schedule_timing(frame: bytes) -> ScheduleTiming:
    """Strict fixed-offset layout verified in protocol §8d; never scan offsets.

    Time block20:40 is start, four repeated boundaries, then final boundary.
    Only the captured 151-byte reply layout is supported. Unknown product codes,
    lengths, invalid BCD, duplicate mismatch or overlapping cycles fail.
    Clock14:20 is the local YY MM DD hh mm ss header; caller checks clock skew.
    """
    from datetime import datetime

    code, cmd, _ = parse_frame(frame)
    if cmd != CMD_READ_CONFIG or code != DEFAULT_DEVICE_CODE or len(frame) != 151:
        raise ValueError("unverified schedule timing layout")

    def bcd(value: int) -> int:
        if value >> 4 > 9 or value & 15 > 9:
            raise ValueError("invalid timing BCD")
        return (value >> 4) * 10 + (value & 15)

    clock = tuple(bcd(v) for v in frame[14:20])
    datetime(2000 + clock[0], *clock[1:])  # calendar/range validation
    pairs = []
    for i in range(20, 40, 2):
        hour, minute = bcd(frame[i]), bcd(frame[i + 1])
        if hour > 23 or minute > 59:
            raise ValueError("invalid schedule clock")
        pairs.append(hour * 60 + minute)
    if any(pairs[i] != pairs[i + 1] for i in (1, 3, 5, 7)):
        raise ValueError("nonstandard repeated schedule boundaries")
    boundaries = tuple(pairs[i] for i in (0, 1, 3, 5, 7, 9))
    duration = sum((end - start) % 1440 for start, end in zip(boundaries, boundaries[1:]))
    if not 0 < duration <= 1440:
        raise ValueError("ambiguous or overlapping daily schedule")
    return ScheduleTiming(boundaries, clock)


def parse_schedule_brightness(frame: bytes) -> list[tuple[int, int, int, int]]:
    """Parse the per-slot brightness from a 0x10 config reply.

    Returns ``NUM_SLOTS`` tuples of four raw-percent channel values
    (``slot0:A B C D, ...``). See §8c — the stored byte is the displayed %.
    """
    device_code, cmd, _ = parse_frame(frame)
    if cmd != CMD_READ_CONFIG:
        raise ValueError(f"not a config reply (cmd 0x{cmd:02X})")
    block = frame[SCHEDULE_OFFSET : SCHEDULE_OFFSET + NUM_SLOTS * NUM_CHANNELS]
    if len(block) < NUM_SLOTS * NUM_CHANNELS:
        raise ValueError("config reply too short for schedule")
    return [
        tuple(block[s * NUM_CHANNELS + c] for c in range(NUM_CHANNELS))
        for s in range(NUM_SLOTS)
    ]


def build_read_options(device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build the read-option-state frame (CMD 0x20)."""
    return build_frame(CMD_READ_OPTIONS, device_code=device_code)


def build_set_options(
    auto_cloud: int,
    phase: int,
    coral: int,
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build the set-options frame (CMD 0x14): [auto_cloud, phase, coral]."""
    payload = bytes([auto_cloud & 0xFF, phase & 0xFF, coral & 0xFF])
    return build_frame(CMD_SET_OPTIONS, payload, device_code=device_code)


def build_set_moon(on: bool, *, device_code: bytes = DEFAULT_DEVICE_CODE) -> bytes:
    """Build native Moon Light (CMD 0x19), separate from the 0x14 phase byte."""
    return build_frame(CMD_SET_MOON, bytes([1 if on else 0]), device_code=device_code)


def build_set_fade(
    on: bool, minutes: int, *, device_code: bytes = DEFAULT_DEVICE_CODE
) -> bytes:
    """Build the set-fade frame (CMD 0x22): [enable, minutes]."""
    payload = bytes([1 if on else 0, max(0, min(255, int(minutes)))])
    return build_frame(CMD_SET_FADE, payload, device_code=device_code)


@dataclass(frozen=True)
class OptionState:
    """Parsed option switches from a 0x20 reply."""

    auto_cloud: int
    phase: int
    coral: int  # 0 = off; 1-10 = acclimation day while running
    moon: int
    fade_enable: int = 0
    fade_minutes: int = 0


def parse_options(frame: bytes) -> OptionState:
    """Parse a 0x20 option-state reply."""
    _device_code, cmd, _payload = parse_frame(frame)
    if cmd != CMD_READ_OPTIONS:
        raise ValueError(f"not an option reply (cmd 0x{cmd:02X})")
    o = OPTIONS_OFFSET
    if len(frame) < o + 4:
        raise ValueError("option reply too short")
    fade_en = frame[FADE_ENABLE_OFFSET] if len(frame) > FADE_ENABLE_OFFSET else 0
    fade_min = frame[FADE_MINUTES_OFFSET] if len(frame) > FADE_MINUTES_OFFSET else 0
    return OptionState(
        frame[o], frame[o + 1], frame[o + 2], frame[o + 3], fade_en, fade_min
    )


def parse_beacon(frame: bytes) -> tuple[bytes, str]:
    """Parse a discovery beacon reply into (device_code, name).

    Example: ``DD 00 0F 01023A01 01 414544433435 030400 33 CC`` -> name "AEDC45".
    """
    device_code, _cmd, payload = parse_frame(frame)
    name = payload[0:6].decode("ascii", errors="replace").strip("\x00").strip()
    return device_code, name


def parse_status(frame: bytes) -> DeviceStatus:
    """Parse a 0x0C read-status reply into a :class:`DeviceStatus`.

    The channel count is detected from the payload length (not hardcoded), so
    non-M5 Horizon Aqua lights with a different number of channels parse too.
    payload = name(6) + N x setpoint (2B) + N x raw (2B), so N = (len-6)/4.
    """
    device_code, cmd, payload = parse_frame(frame)
    if cmd != CMD_READ_STATUS:
        raise ValueError(f"not a status reply (cmd 0x{cmd:02X})")
    if len(payload) < 6 + 4:
        raise ValueError("status payload too short")
    n = (len(payload) - 6) // 4  # channels
    name = payload[0:6].decode("ascii", errors="replace").strip("\x00")
    pos = 6
    setpoints = tuple(
        int.from_bytes(payload[pos + i * 2 : pos + i * 2 + 2], "big") for i in range(n)
    )
    pos += n * 2
    raw = tuple(
        int.from_bytes(payload[pos + i * 2 : pos + i * 2 + 2], "big") for i in range(n)
    )
    return DeviceStatus(device_code=device_code, name=name, setpoints=setpoints, raw=raw)

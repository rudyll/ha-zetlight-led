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
CMD_START = 0x1E         # turn on / resume (device-verified)
CMD_OFF = 0x1F           # turn off (device-verified)

NUM_SLOTS = 5  # the device's daily schedule has 5 time slots

# New-protocol discovery probe broadcast to :8855; devices answer with a
# ``DD...CC`` beacon that carries their device code and name.
DISCOVERY_FRAME = bytes.fromhex("C9000000000A021D")

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


def build_brightness(
    channels: tuple[int, int, int, int],
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build a dimming frame (CMD 0x13) for the four channels (each 0-100).

    Payload is ``<i> <c1> <c2> <c3> <c4> <i6>`` where ``i`` and ``i6`` are both
    0x00 and each ``c`` is the BCD-encoded brightness (100 -> 0xAA). This is a
    real-time preview command: it sets the live output but does NOT write the
    device's stored time-curve program. Device-verified (docs §6b):

    * all 10% -> ``EE000C01023A011300101010100027CC``
    * all 100% -> ``EE000C01023A011300AAAAAAAA0027CC``
    """
    if len(channels) != NUM_CHANNELS:
        raise ValueError(f"expected {NUM_CHANNELS} channel values")
    payload = (
        bytes([SET_LIGHT_PREFIX])
        + bytes(_to_bcd(c) for c in channels)
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

    ``slots`` is the daily curve: ``NUM_SLOTS`` tuples of four channel values
    (0-100), laid out ``slot0:A B C D, slot1:A B C D, ...`` as BCD (100 -> 0xAA).
    Mirrors the app's ``sendSaveFivelight`` / ``sendSaveFivelightLED``.

    WARNING: this overwrites the device's stored brightness program.
    """
    if len(slots) != NUM_SLOTS:
        raise ValueError(f"expected {NUM_SLOTS} slots")
    payload = bytearray()
    for slot in slots:
        if len(slot) != NUM_CHANNELS:
            raise ValueError(f"each slot needs {NUM_CHANNELS} channel values")
        payload += bytes(_to_bcd(c) for c in slot)
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


def parse_status(frame: bytes) -> DeviceStatus:
    """Parse a 0x0C read-status reply into a :class:`DeviceStatus`."""
    device_code, cmd, payload = parse_frame(frame)
    if cmd != CMD_READ_STATUS:
        raise ValueError(f"not a status reply (cmd 0x{cmd:02X})")
    # payload = name(6) + 4x setpoint (2B each) + 4x raw (2B each) = 22 bytes
    if len(payload) < 6 + NUM_CHANNELS * 2 * 2:
        raise ValueError("status payload too short")
    name = payload[0:6].decode("ascii", errors="replace").strip("\x00")
    pos = 6
    setpoints = tuple(
        int.from_bytes(payload[pos + i * 2 : pos + i * 2 + 2], "big")
        for i in range(NUM_CHANNELS)
    )
    pos += NUM_CHANNELS * 2
    raw = tuple(
        int.from_bytes(payload[pos + i * 2 : pos + i * 2 + 2], "big")
        for i in range(NUM_CHANNELS)
    )
    return DeviceStatus(device_code=device_code, name=name, setpoints=setpoints, raw=raw)

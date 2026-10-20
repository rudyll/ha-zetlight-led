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
CMD_READ_STATUS = 0x0C  # read live lighting status (read-only)
CMD_SET_LIGHT = 0x13    # set per-channel brightness (TODO: i/i6 params)
CMD_START = 0x1E        # turn on / resume (device-verified)
CMD_OFF = 0x1F          # turn off (device-verified)

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


def build_set_light(
    channels: tuple[int, int, int, int],
    *,
    device_code: bytes = DEFAULT_DEVICE_CODE,
) -> bytes:
    """Build a dimming frame (CMD 0x13) — SKELETON, NOT YET SAFE TO SEND.

    TODO: the ``i`` (leading) and ``i6`` (trailing) auxiliary bytes of the
    ``sendlight`` payload are not yet pinned down (group index / fade?). Until
    one more capture confirms them, this function is a structural placeholder
    and must not be wired up to a live device. See docs §5 and §6.
    """
    raise NotImplementedError(
        "0x13 dimming is not implemented yet: the i/i6 auxiliary payload bytes "
        "still need one capture to confirm. See docs/m5-light-protocol.md."
    )
    # Intended shape once i/i6 are known:
    #   payload = bytes([i]) + bytes(_to_bcd(c) for c in channels) + bytes([i6])
    #   return build_frame(CMD_SET_LIGHT, payload, device_code=device_code)


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

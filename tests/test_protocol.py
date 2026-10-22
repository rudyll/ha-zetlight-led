"""Unit tests for the Zetlight M5 protocol layer.

These assert against frames captured from a real M5-80M device (see
docs/m5-light-protocol.md §4 and §6). They have no Home Assistant dependency.
"""

import os
import sys

import pytest

sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "custom_components", "zetlight_led")
)

import protocol  # noqa: E402

DEVICE = protocol.DEFAULT_DEVICE_CODE  # 01 02 3A 01


def test_device_code_default():
    assert DEVICE == bytes.fromhex("01023A01")


def test_build_off_matches_device():
    # Verified on device: light physically turned off.
    assert protocol.build_off().hex().upper() == "EE000601023A011F21CC"


def test_build_on_matches_device():
    # Verified on device: light physically turned on.
    assert protocol.build_on().hex().upper() == "EE000601023A011E20CC"


def test_build_read_status_matches_device():
    assert protocol.build_read_status().hex().upper() == "EE000601023A010C32CC"


def test_build_frame_length_and_xor():
    frame = protocol.build_frame(protocol.CMD_OFF)
    assert frame[0] == protocol.REQUEST_HEADER
    assert frame[-1] == protocol.TRAILER
    assert frame[2] == 6  # device(4) + cmd(1) + payload(0) + xor(1)


def test_build_frame_rejects_bad_device_code():
    with pytest.raises(ValueError):
        protocol.build_frame(protocol.CMD_OFF, device_code=b"\x01\x02")


def test_parse_status_from_captured_reply():
    # Captured 0x0C reply from the real device.
    reply = bytes.fromhex(
        "DD001C01023A010C"
        "414544433435"  # name "AEDC45"
        "0037003700370037"  # 4x setpoint = 55
        "0546056E05320514"  # 4x raw
        "24CC"
    )
    status = protocol.parse_status(reply)
    assert status.device_code == DEVICE
    assert status.name == "AEDC45"
    assert status.setpoints == (0x37, 0x37, 0x37, 0x37)
    assert status.raw == (0x0546, 0x056E, 0x0532, 0x0514)


def test_parse_frame_round_trips_a_built_frame():
    # A request frame uses the EE header, so parse_frame (which expects DD)
    # should reject it — confirms header validation.
    with pytest.raises(ValueError):
        protocol.parse_frame(protocol.build_off())


def test_parse_frame_detects_xor_error():
    reply = bytearray(
        bytes.fromhex(
            "DD001C01023A010C4145444334350037003700370037"
            "0546056E0532051424CC"
        )
    )
    reply[-2] ^= 0xFF  # corrupt the XOR byte
    with pytest.raises(ValueError):
        protocol.parse_frame(bytes(reply))


def test_parse_frame_detects_bad_trailer():
    reply = bytes.fromhex(
        "DD001C01023A010C4145444334350037003700370037"
        "0546056E0532051424FF"  # trailer should be CC
    )
    with pytest.raises(ValueError):
        protocol.parse_frame(reply)


def test_to_bcd_encoding():
    assert protocol._to_bcd(0) == 0x00
    assert protocol._to_bcd(50) == 0x50
    assert protocol._to_bcd(55) == 0x55
    assert protocol._to_bcd(100) == 0xAA  # special-cased
    with pytest.raises(ValueError):
        protocol._to_bcd(101)


def test_build_brightness_all_10_percent():
    # Verified on device: all channels at 10%.
    assert (
        protocol.build_brightness((10, 10, 10, 10)).hex().upper()
        == "EE000C01023A011300101010100027CC"
    )


def test_build_brightness_all_100_percent():
    # Verified on device: all channels at 100% (BCD special-cased to 0xAA).
    assert (
        protocol.build_brightness((100, 100, 100, 100)).hex().upper()
        == "EE000C01023A011300AAAAAAAA0027CC"
    )


def test_build_brightness_mixed_channels():
    # (0, 30, 55, 100) -> payload i(00) + 00 30 55 AA + i6(00)
    frame = protocol.build_brightness((0, 30, 55, 100))
    assert frame[0] == protocol.REQUEST_HEADER
    assert frame[7] == protocol.CMD_SET_LIGHT
    assert frame[8:14] == bytes.fromhex("00003055AA00")
    assert frame[-1] == protocol.TRAILER


def _status_reply(setpoints, raw):
    """Build a synthetic 0x0C reply with N channels (for the parser test)."""
    code = protocol.DEFAULT_DEVICE_CODE
    payload = (
        b"AEDC45"
        + b"".join(s.to_bytes(2, "big") for s in setpoints)
        + b"".join(r.to_bytes(2, "big") for r in raw)
    )
    length = 4 + 1 + len(payload) + 1
    middle = bytes([0x00, length]) + code + bytes([protocol.CMD_READ_STATUS]) + payload
    x = 0
    for b in middle:
        x ^= b
    return bytes([0xDD]) + middle + bytes([x & 0xFF, 0xCC])


def test_parse_status_detects_channel_count():
    # A 6-channel model parses to 6 setpoints/raw (not hardcoded to 4).
    frame = _status_reply([10, 20, 30, 40, 50, 60], [1, 2, 3, 4, 5, 6])
    st = protocol.parse_status(frame)
    assert st.setpoints == (10, 20, 30, 40, 50, 60)
    assert st.raw == (1, 2, 3, 4, 5, 6)


def test_build_brightness_accepts_any_channel_count():
    # Non-4-channel models are supported; empty is rejected.
    assert protocol.build_brightness((50, 50, 50))[7] == protocol.CMD_SET_LIGHT
    assert protocol.build_brightness((10,) * 6)[7] == protocol.CMD_SET_LIGHT
    with pytest.raises(ValueError):
        protocol.build_brightness(())


def _assert_request(frame: bytes, cmd: int, payload: bytes) -> None:
    """Validate an EE... request frame's header/cmd/payload/XOR/trailer."""
    assert frame[0] == protocol.REQUEST_HEADER
    assert frame[-1] == protocol.TRAILER
    assert frame[3:7] == protocol.DEFAULT_DEVICE_CODE
    assert frame[7] == cmd
    assert frame[8:-2] == payload
    assert frame[2] == len(protocol.DEFAULT_DEVICE_CODE) + 1 + len(payload) + 1
    assert protocol._xor(frame[1:-2]) == frame[-2]


def test_build_read_config_matches_device():
    # Confirmed against the real device probe.
    assert protocol.build_read_config().hex().upper() == "EE000601023A01102ECC"


def test_build_time_sync_layout():
    frame = protocol.build_time_sync(2026, 10, 21, 12, 34, 56)
    _assert_request(frame, protocol.CMD_SYNC_TIME, bytes.fromhex("261021123456"))


def test_build_schedule_brightness_ui_curve():
    # The five slots from the app screenshots (A, B, C, D percentages).
    slots = [
        (2, 18, 18, 2),
        (4, 36, 24, 4),
        (10, 90, 60, 10),
        (6, 54, 36, 6),
        (3, 27, 18, 3),
    ]
    frame = protocol.build_schedule_brightness(slots)
    # Raw-percent bytes (device-verified): stored byte == displayed %.
    expected = bytes.fromhex("02121202" "04241804" "0A5A3C0A" "06362406" "031B1203")
    _assert_request(frame, protocol.CMD_SAVE_SCHEDULE, expected)
    assert frame[2] == 0x1A  # LEN


def test_build_schedule_brightness_raw_and_overdrive():
    frame = protocol.build_schedule_brightness([(100, 50, 0, 144)] * protocol.NUM_SLOTS)
    assert frame[8:12] == bytes([0x64, 0x32, 0x00, 0x90])  # 100->0x64, overdrive 144 ok


def test_build_schedule_times_ui_schedule():
    # 07:30 start; slots 60/120/480/120/120 min -> boundaries 08:30,10:30,18:30,20:30,22:30
    frame = protocol.build_schedule_times(7 * 60 + 30, [60, 120, 480, 120, 120])
    expected = bytes.fromhex(
        "0730" "0830" "0830" "1030" "1030" "1830" "1830" "2030" "2030" "2230"
    )
    _assert_request(frame, protocol.CMD_SAVE_TIMES, expected)
    assert frame[2] == 0x1A  # LEN


def test_build_set_options_coral_on():
    frame = protocol.build_set_options(0, 0, 1)
    _assert_request(frame, protocol.CMD_SET_OPTIONS, bytes([0, 0, 1]))


def test_build_set_moon():
    _assert_request(protocol.build_set_moon(True), protocol.CMD_SET_MOON, bytes([1]))
    _assert_request(protocol.build_set_moon(False), protocol.CMD_SET_MOON, bytes([0]))


def test_build_set_fade():
    _assert_request(protocol.build_set_fade(True, 15), protocol.CMD_SET_FADE, bytes([1, 15]))
    _assert_request(protocol.build_set_fade(False, 3), protocol.CMD_SET_FADE, bytes([0, 3]))


def test_parse_options_from_captured_reply():
    # Captured 0x20 reply: moon on, coral off, fade on 15 min.
    reply = bytes.fromhex("DD001701023A0120414544433435000000010000000000010F02CC")
    opts = protocol.parse_options(reply)
    assert (opts.auto_cloud, opts.phase, opts.coral, opts.moon) == (0, 0, 0, 1)
    assert (opts.fade_enable, opts.fade_minutes) == (1, 15)

    # And the enabled-coral reply.
    reply_on = bytes.fromhex("DD001701023A0120414544433435000001010000000000010F03CC")
    assert protocol.parse_options(reply_on).coral == 1


def test_parse_beacon():
    # Discovery beacon from the docs.
    code, name = protocol.parse_beacon(
        bytes.fromhex("DD000F01023A010141454443343503040033CC")
    )
    assert code == protocol.DEFAULT_DEVICE_CODE
    assert name == "AEDC45"


def test_parse_schedule_brightness_from_captured_reply():
    # Real 0x10 config reply captured from the device.
    reply = bytes.fromhex(
        "DD009301023A0110"
        "414544433435"  # name AEDC45
        "2610210043270900"  # date/time + misc
        "100010001200120020002000220022000000"  # misc
        "040E1E0C081C3C181446963C0C2A5A2406152D12"  # <- schedule brightness (offset 40)
        "05010000000101FFFFFFFF000000522240"
        "303130303030303030333030303030313031303330303030303030303030303030303030303030303030303030303030303030303030303030313030222C227A65746C696768742248"
        "CC"
    )
    slots = protocol.parse_schedule_brightness(reply)
    assert slots == [
        (4, 14, 30, 12),
        (8, 28, 60, 24),
        (20, 70, 150, 60),
        (12, 42, 90, 36),
        (6, 21, 45, 18),
    ]


def test_schedule_builders_reject_wrong_counts():
    with pytest.raises(ValueError):
        protocol.build_schedule_brightness([(0, 0, 0, 0)])  # not 5 slots
    with pytest.raises(ValueError):
        protocol.build_schedule_times(0, [60, 60])  # not 5 durations

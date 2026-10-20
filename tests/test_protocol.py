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


def test_build_brightness_rejects_wrong_channel_count():
    with pytest.raises(ValueError):
        protocol.build_brightness((50, 50, 50))  # type: ignore[arg-type]


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
    expected = bytes.fromhex("02181802" "04362404" "10906010" "06543606" "03271803")
    _assert_request(frame, protocol.CMD_SAVE_SCHEDULE, expected)
    assert frame[2] == 0x1A  # LEN


def test_build_schedule_brightness_handles_100():
    slots = [(100, 0, 0, 0)] * protocol.NUM_SLOTS
    frame = protocol.build_schedule_brightness(slots)
    assert frame[8] == 0xAA  # 100 -> 0xAA


def test_build_schedule_times_ui_schedule():
    # 07:30 start; slots 60/120/480/120/120 min -> boundaries 08:30,10:30,18:30,20:30,22:30
    frame = protocol.build_schedule_times(7 * 60 + 30, [60, 120, 480, 120, 120])
    expected = bytes.fromhex(
        "0730" "0830" "0830" "1030" "1030" "1830" "1830" "2030" "2030" "2230"
    )
    _assert_request(frame, protocol.CMD_SAVE_TIMES, expected)
    assert frame[2] == 0x1A  # LEN


def test_schedule_builders_reject_wrong_counts():
    with pytest.raises(ValueError):
        protocol.build_schedule_brightness([(0, 0, 0, 0)])  # not 5 slots
    with pytest.raises(ValueError):
        protocol.build_schedule_times(0, [60, 60])  # not 5 durations

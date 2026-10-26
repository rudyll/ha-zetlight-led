"""Constants for the Zetlight Horizon Aqua LED integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "zetlight_led"

# UDP port the M5 (and other old-protocol LED devices) listens/replies on.
DEFAULT_PORT = 8855

# Config entry / flow keys.
CONF_DEVICE_CODE = "device_code"
# Options key: a mapping of preset name -> {start, durations, brightness}.
CONF_PRESETS = "presets"
# Options key: status poll interval in seconds.
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_SECONDS = 30

# Discovery broadcast timeout (seconds).
DISCOVERY_TIMEOUT = 2.0

# How often the coordinator polls the device status (0x0C). On/off is not
# readable, so this mainly tracks reachability and the configured setpoints.
SCAN_INTERVAL = timedelta(seconds=30)

# Network timeout for a single request/response round trip.
REQUEST_TIMEOUT = 3.0

# Custom lightning effect defaults (built from live 0x13 frames, not the
# vendor's effect command). Flashes channels A+B only; on the confirmed
# M5-80M these are white + UV violet.
LIGHTNING_DEFAULT_FLASHES = 3      # number of strokes per bolt
LIGHTNING_DEFAULT_INTENSITY = 100  # peak A/B level per flash (0-100)
LIGHTNING_DEFAULT_ON_MS = 80       # on-time per flash, milliseconds

# Feeding / maintenance mode: temporarily dim all channels, then auto-restore.
FEEDING_DEFAULT_LEVEL = 20      # channel level while feeding (0-100)
FEEDING_DEFAULT_MINUTES = 10    # auto-restore after this many minutes

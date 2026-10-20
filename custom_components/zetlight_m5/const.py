"""Constants for the Zetlight M5 integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "zetlight_m5"

# UDP port the M5 (and other old-protocol LED devices) listens/replies on.
DEFAULT_PORT = 8855

# Config entry / flow keys.
CONF_DEVICE_CODE = "device_code"

# How often the coordinator polls the device status (0x0C). On/off is not
# readable, so this mainly tracks reachability and the configured setpoints.
SCAN_INTERVAL = timedelta(seconds=30)

# Network timeout for a single request/response round trip.
REQUEST_TIMEOUT = 3.0

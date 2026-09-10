"""Control policy independent of ROS; all times use a monotonic clock."""

import json
import math

MOVE = 1008
STOP = 1003


def request_fields(command):
    """Return official Unitree API ID and JSON parameter for (vx, yaw)."""
    vx, yaw = command
    if vx == 0.0 and yaw == 0.0:
        return STOP, ''
    return MOVE, json.dumps({'x': vx, 'y': 0.0, 'z': yaw}, allow_nan=False)


class Control:
    def __init__(self, max_linear=0.2, max_yaw=0.4, timeout=0.5, stop_duration=0.5):
        for name, value in [('max_linear', max_linear), ('max_yaw', max_yaw),
                            ('timeout', timeout), ('stop_duration', stop_duration)]:
            if not math.isfinite(value) or value <= 0:
                raise ValueError(name + ' must be finite and positive')
        self.max_linear = max_linear
        self.max_yaw = max_yaw
        self.timeout = timeout
        self.stop_duration = stop_duration
        self.command = (0.0, 0.0)
        self.last_input = None
        self.stop_until = None
        self.active = False

    def stop(self, now):
        self.command = (0.0, 0.0)
        self.stop_until = now + self.stop_duration
        self.active = True

    def receive(self, linear, angular, now):
        # Reject unsupported axes instead of partially executing an invalid Twist.
        if not all(math.isfinite(v) for v in (*linear, *angular)):
            self.stop(now)
            return False
        if any(v != 0.0 for v in (linear[1], linear[2], angular[0], angular[1])):
            self.stop(now)
            return False
        self.last_input = now
        self.command = (
            max(-self.max_linear, min(self.max_linear, linear[0])),
            max(-self.max_yaw, min(self.max_yaw, angular[2])),
        )
        self.active = True
        self.stop_until = None
        if self.command == (0.0, 0.0):
            self.stop(now)
        return True

    def sample(self, now):
        if not self.active:
            return None
        if self.stop_until is None and now - self.last_input >= self.timeout:
            self.stop(now)
        if self.stop_until is not None and now >= self.stop_until:
            self.active = False
            return None
        return self.command

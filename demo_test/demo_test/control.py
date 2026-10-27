"""ROS-independent front point detection and stop/resume state."""

import math


DEFAULTS = dict(
    vx=0.3, yaw=0.3, stop_distance=1.0, front_angle_deg=60.0,
    min_height=-0.2, max_height=0.5, lidar_timeout=0.5,
    clear_duration=0.5, publish_rate=20.0,
)


class CircleControl:
    """Use monotonic seconds; point coordinates must be robot-aligned."""

    def __init__(self, **settings):
        self.p = dict(DEFAULTS, **settings)
        p = self.p
        if not all(math.isfinite(v) for v in p.values()):
            raise ValueError('All numeric parameters must be finite')
        if not (0 < p['vx'] <= 0.3 and 0 < abs(p['yaw']) <= 0.4):
            raise ValueError('Require 0 < vx <= 0.3 and 0 < abs(yaw) <= 0.4')
        if not (p['stop_distance'] > 0 and 0 < p['front_angle_deg'] <= 180):
            raise ValueError('Invalid distance or front angle')
        if not (p['min_height'] < p['max_height']):
            raise ValueError('min_height must be less than max_height')
        if not (p['lidar_timeout'] > 0 and p['clear_duration'] >= 0
                and 5 <= p['publish_rate'] <= 100):
            raise ValueError('Invalid timeout, clear duration or publish rate')
        self.last_scan = None
        self.clear_since = None
        # 주행은 라이다 첫 수신과 무관하게 시작한다.
        self.stopped = False

    def invalidate(self):
        self.last_scan = None
        self.clear_since = None
        self.stopped = True

    def observe(self, points, now):
        p = self.p
        valid = False
        blocked = False
        for x, y, z in points:
            if not all(math.isfinite(float(v)) for v in (x, y, z)):
                continue
            if x == 0 and y == 0 and z == 0:
                continue
            valid = True
            if (x > 0 and p['min_height'] <= z <= p['max_height']
                    and abs(math.atan2(y, x)) <= math.radians(p['front_angle_deg'] / 2)
                    and math.hypot(x, y) <= p['stop_distance']):
                blocked = True
                break
        if not valid:
            self.invalidate()
            return
        previous = self.last_scan
        self.last_scan = now
        if blocked:
            self.stopped = True
            self.clear_since = None
        elif (self.stopped or (previous is not None
                              and now - previous >= p['lidar_timeout'])):
            self.stopped = True
            if (self.clear_since is None or previous is None
                    or now - previous >= p['lidar_timeout']):
                self.clear_since = now

    def command(self, now):
        # 첫 입력 대기는 하지 않는다. 수신을 시작한 뒤의 끊김은 정지한다.
        if (self.last_scan is not None
                and now - self.last_scan >= self.p['lidar_timeout']):
            self.stopped = True
            self.clear_since = None
        if self.stopped:
            if (self.clear_since is None
                    or now - self.clear_since < self.p['clear_duration']):
                return 0.0, 0.0
            self.stopped = False
            self.clear_since = None
        return self.p['vx'], self.p['yaw']

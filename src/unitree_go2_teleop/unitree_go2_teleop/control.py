"""ROS와 독립적인 속도 제한 및 정지 처리. now는 monotonic 시간(초)."""

import json
import math


MOVE = 1008
STOP = 1003
ZERO_COMMAND = (0.0, 0.0, 0.0)
MAX_SAMPLE_DT = 0.1
STOP_EPSILON = 0.01  # 선속도는 m/s, 각속도는 rad/s 기준


def clamp(value, limit):
    """값을 [-limit, limit] 범위로 제한합니다."""
    return max(-limit, min(limit, value))


def move_towards(current, target, max_delta):
    """목표를 넘지 않도록 한 스텝의 변화량을 제한합니다."""
    if target > current:
        return min(current + max_delta, target)
    if target < current:
        return max(current - max_delta, target)
    return target


def slew_velocity(current, target, accel, decel, dt):
    """방향 반전 시 먼저 0까지 감속한 뒤 다음 스텝부터 가속합니다."""
    if current * target < 0.0:
        return move_towards(current, 0.0, decel * dt)

    rate = accel if abs(target) > abs(current) else decel
    return move_towards(current, target, rate * dt)


def request_fields(command, *, stop=False):
    """일시적인 속도 0과 명시적인 StopMove 요청을 구분합니다."""
    if stop:
        return STOP, '{}'

    vx, vy, yaw = command
    return MOVE, json.dumps(
        {'x': vx, 'y': vy, 'z': yaw},
        allow_nan=False,
    )


class Control:
    """이동 → 타임아웃 감속 → 정지 반복 전송 → 비활성 상태를 관리합니다."""

    def __init__(
        self,
        max_linear=0.3,
        max_lateral=0.3,
        max_yaw=0.4,
        timeout=0.5,
        stop_duration=0.5,
        linear_accel=0.25,
        linear_decel=0.45,
        lateral_accel=0.25,
        lateral_decel=0.45,
        yaw_accel=0.8,
        yaw_decel=1.0,
    ):
        settings = {
            'max_linear': max_linear,
            'max_lateral': max_lateral,
            'max_yaw': max_yaw,
            'timeout': timeout,
            'stop_duration': stop_duration,
            'linear_accel': linear_accel,
            'linear_decel': linear_decel,
            'lateral_accel': lateral_accel,
            'lateral_decel': lateral_decel,
            'yaw_accel': yaw_accel,
            'yaw_decel': yaw_decel,
        }
        for name, value in settings.items():
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(name + ' must be finite and positive')

        self.max_linear = max_linear
        self.max_lateral = max_lateral
        self.max_yaw = max_yaw
        self.timeout = timeout
        self.stop_duration = stop_duration
        self.linear_accel = linear_accel
        self.linear_decel = linear_decel
        self.lateral_accel = lateral_accel
        self.lateral_decel = lateral_decel
        self.yaw_accel = yaw_accel
        self.yaw_decel = yaw_decel

        self.command = ZERO_COMMAND
        self.target_command = ZERO_COMMAND        
        self.last_input = None
        self.last_sample_time = None
        self.stop_until = None
        self.active = False
        self.slowing_down = False

    @property
    def stop_requested(self):
        """StopMove를 반복 발행하는 상태인지 반환합니다."""
        return self.stop_until is not None

    def stop(self, now):
        """감속을 생략하고 즉시 정지 요청 상태로 전환합니다."""
        self.target_command = ZERO_COMMAND
        self.command = ZERO_COMMAND
        self.last_sample_time = None
        self.stop_until = now + self.stop_duration
        self.slowing_down = False
        self.active = True

    def begin_slowdown(self, now):
        """타임아웃 시 현재 출력 속도에서 0까지 감속합니다."""
        self.target_command = ZERO_COMMAND
        self.slowing_down = True
        self.stop_until = None
        self.active = True

    def receive(self, linear, angular, now):
        """Twist의 두 3축 벡터를 받아 목표 속도를 갱신합니다."""
        finite = all(math.isfinite(v) for v in (*linear, *angular))
        supported = all(v == 0.0 for v in (linear[2], angular[0], angular[1]))
        if not finite or not supported:
            self.stop(now)
            return False

        self.last_input = now
        target = (
            clamp(linear[0], self.max_linear),
            clamp(linear[1], self.max_lateral),
            clamp(angular[2], self.max_yaw),
        )
        if target == ZERO_COMMAND:
            self.stop(now)
            return True

        if self.last_sample_time is None:
            self.last_sample_time = now

        self.target_command = target
        self.active = True
        self.slowing_down = False
        self.stop_until = None
        return True

    def sample(self, now):
        """발행할 (vx, vy, yaw)를 반환합니다. None이면 발행하지 않습니다."""
        if not self.active:
            return None

        if self.stop_requested:
            if now >= self.stop_until:
                self.active = False
                self.stop_until = None
                return None          
            return ZERO_COMMAND

        if (
            not self.slowing_down
            and self.last_input is not None
            and now - self.last_input >= self.timeout
        ):
            self.begin_slowdown(now)

        dt = 0.0 if self.last_sample_time is None else now - self.last_sample_time
        dt = max(0.0, min(dt, MAX_SAMPLE_DT))
        self.last_sample_time = now

        rates = (
            (self.linear_accel, self.linear_decel),
            (self.lateral_accel, self.lateral_decel),
            (self.yaw_accel, self.yaw_decel),
        )
        self.command = tuple(
            slew_velocity(current, target, accel, decel, dt)
            for current, target, (accel, decel) in zip(
                self.command, self.target_command, rates
            )
        )

        if self.slowing_down and all(abs(v) < STOP_EPSILON for v in self.command):
            self.stop(now)

        return self.command
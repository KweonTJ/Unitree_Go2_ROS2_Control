#!/usr/bin/env python3

import time
import math
import signal
import rclpy
import queue
import threading
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from unitree_go.msg import LowState

def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def validate_command(vx, vy, yaw, duration):
    if not all(math.isfinite(v) for v in (vx, vy, yaw, duration)):
        raise ValueError('vx, vy, yaw and duration must be finite')
    if duration <= 0.0:
        raise ValueError('duration must be positive')
    if abs(vx) > 0.3 or abs(vy) > 0.3 or abs(yaw) > 0.4:
        raise ValueError('velocity limits: vx/vy +/-0.3 m/s, yaw +/-0.4 rad/s')


class TimedTrajectory(Node):

    def __init__(self):
        super().__init__('timed_trajectory')

        # -----------------------------
        # ROS2 Parameters
        # -----------------------------
        self.declare_parameter('output_topic', '/cmd_vel')
        self.declare_parameter('interactive', True)

        self.declare_parameter('vx', 0.0)
        self.declare_parameter('vy', 0.0)
        self.declare_parameter('yaw', 0.0)

        self.declare_parameter('duration', 5.0)
        self.declare_parameter('publish_rate', 50.0)

        self.declare_parameter('lowstate_topic', '/lowstate')
        self.declare_parameter('heading_control', True)

        self.declare_parameter('kp_yaw', 1.0)
        self.declare_parameter('ki_yaw', 0.0)
        self.declare_parameter('kd_yaw', 0.05)

        self.declare_parameter('max_yaw_correction', 0.15)

        # -----------------------------
        # Parameter values
        # -----------------------------
        self.output_topic = self.get_parameter('output_topic').value
        self.interactive = self.get_parameter('interactive').value
        self.vx = float(self.get_parameter('vx').value)
        self.vy = float(self.get_parameter('vy').value)
        self.yaw = float(self.get_parameter('yaw').value)
        self.duration = float(self.get_parameter('duration').value)
        self.publish_rate = float(self.get_parameter('publish_rate').value)
        self.lowstate_topic = self.get_parameter('lowstate_topic').value
        self.heading_control = bool(self.get_parameter('heading_control').value)
        self.kp_yaw = float(self.get_parameter('kp_yaw').value)
        self.ki_yaw = float(self.get_parameter('ki_yaw').value)
        self.kd_yaw = float(self.get_parameter('kd_yaw').value)
        self.max_yaw_correction = float(self.get_parameter('max_yaw_correction').value)

        validate_command(self.vx, self.vy, self.yaw, self.duration)
        # The bundled bridge stops after 0.5 s without a command.
        if not math.isfinite(self.publish_rate) or not 5.0 <= self.publish_rate <= 100.0:
            raise ValueError('publish_rate must be between 5 and 100 Hz')
        for name in ('kp_yaw', 'ki_yaw', 'kd_yaw'):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(name + ' must be finite and non-negative')
        if (
            not math.isfinite(self.max_yaw_correction)
            or not 0.0 <= self.max_yaw_correction <= 0.4
        ):
            raise ValueError('max_yaw_correction must be between 0 and 0.4 rad/s')

        # -----------------------------
        # Publisher
        # -----------------------------
        self.publisher = self.create_publisher(
            Twist,
            self.output_topic,
            10
        )

        self.lowstate_sub = self.create_subscription(
            LowState,
            self.lowstate_topic,
            self.lowstate_callback,
            qos_profile_sensor_data
        )

        # -----------------------------
        # Trajectory State
        # -----------------------------
        self.running = False
        self.finished = False
        self.start_time = None
        self.wait_started_at = None
        self.stop_ticks = 0

        # -----------------------------
        # Heading PID State
        # -----------------------------
        self.heading_active = False

        self.current_yaw = None
        self.yaw_rate = 0.0
        self.last_imu_time = None

        self.target_yaw = None
        self.yaw_integral = 0.0
        self.last_control_time = None

        # -----------------------------
        # Terminal Input
        # -----------------------------
        self.command_queue = queue.Queue(maxsize=1)
        self.ready_event = threading.Event()
        self.ready_event.set()
        self.shutdown_event = threading.Event()
        self.input_closed = threading.Event()

        # -----------------------------
        # Timer
        # -----------------------------
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(
            1.0 / self.publish_rate,
            self.timer_callback,
            clock=self.steady_clock,
        )

        # -----------------------------
        # Input Thread
        # -----------------------------
        self.input_thread = None
        if self.interactive:
            self.input_thread = threading.Thread(target=self.input_loop, daemon=True)
            self.input_thread.start()
            self.get_logger().info('Trajectory controller ready for terminal input')
        else:
            self.ready_event.clear()
            self.command_queue.put((self.vx, self.vy, self.yaw, self.duration))
            self.get_logger().info('Single trajectory queued from ROS parameters')

    def print_input_context(self):

        print()
        print('==============================================')
        print(' Go2 Trajectory Control')
        print('==============================================')
        print()
        print('입력 순서')
        print()
        print('  vx     vy     yaw     duration')
        print(' [m/s]  [m/s]  [rad/s]    [s]')
        print()
        print(' vx       : +전진 / -후진')
        print(' vy       : +좌측 / -우측')
        print(' yaw      : +좌회전 / -우회전')
        print(' duration : 주행 시간')
        print()
        print('예시')
        print(' 0.3   0     0     5   -> 전진 5초')
        print('-0.3   0     0     3   -> 후진 3초')
        print(' 0     0.3   0     3   -> 좌측 이동 3초')
        print(' 0     0     0.2   2   -> 좌회전 2초')
        print()
        print('Heading PID')
        print(f'Kp={self.kp_yaw:.2f} ' f'Ki={self.ki_yaw:.2f} ' f'Kd={self.kd_yaw:.2f}')
        print()
        print('==============================================')

    def input_loop(self):
        while rclpy.ok() and not self.shutdown_event.is_set():
            # 이전 주행 종료까지 대기
            self.ready_event.wait()
            if not rclpy.ok() or self.shutdown_event.is_set():
                return
            self.print_input_context()
            try:
                raw = input('> ').strip()
            except (EOFError, KeyboardInterrupt):
                self.input_closed.set()
                return
            if not raw:
                continue
            values = raw.split()
            if len(values) != 4:
                print('[ERROR] vx vy yaw duration 순서로 입력하세요.')
                continue
            try:
                vx, vy, yaw, duration = map(float, values)
            except ValueError:
                print('[ERROR] 숫자만 입력하세요.')
                continue
            try:
                validate_command(vx, vy, yaw, duration)
            except ValueError as exc:
                print(f'[ERROR] {exc}')
                continue

            if self.shutdown_event.is_set():
                return
            self.ready_event.clear()

            self.command_queue.put((vx, vy, yaw, duration))

    def start_trajectory(self, vx, vy, yaw, duration):

        validate_command(vx, vy, yaw, duration)
        # 사용자 입력 적용
        self.vx = vx
        self.vy = vy
        self.yaw = yaw
        self.duration = duration

        # Heading PID 활성화 조건
        self.heading_active = (
            self.heading_control
            and abs(self.yaw) < 1e-6
            and (
                abs(self.vx) > 1e-6
                or abs(self.vy) > 1e-6
            )
        )

        # PID 초기화
        self.target_yaw = None
        self.yaw_integral = 0.0
        self.last_control_time = None
        self.running = True

        now = time.monotonic()
        self.wait_started_at = now

        if self.heading_active:
            # 다음 IMU 메시지로 새 Heading 기준 설정
            self.start_time = None
        else:
            self.start_time = now

        self.get_logger().info(
            f'Start trajectory | '
            f'vx={vx:.2f}, '
            f'vy={vy:.2f}, '
            f'yaw={yaw:.2f}, '
            f'duration={duration:.2f}s'
        )

    def lowstate_callback(self, msg):

        yaw = float(msg.imu_state.rpy[2])
        yaw_rate = float(msg.imu_state.gyroscope[2])

        if not (
            math.isfinite(yaw)
            and math.isfinite(yaw_rate)
        ):
            return

        self.current_yaw = yaw
        self.yaw_rate = yaw_rate
        self.last_imu_time = time.monotonic()

        # 최초 방향을 목표 방향으로 설정
        if (
            self.running
            and self.heading_active
            and self.target_yaw is None
        ):
            self
            .target_yaw = yaw

            now = time.monotonic()

            self.start_time = now
            self.last_control_time = now

            self.get_logger().info(
                f'Heading reference set: '
                f'{self.target_yaw:.3f} rad'
            )

    def calculate_yaw_correction(self):
        if (
            self.current_yaw is None
            or self.target_yaw is None
        ):
            return 0.0

        now = time.monotonic()

        error = wrap_angle(
            self.target_yaw
            - self.current_yaw
        )

        dt = 0.0
        if self.last_control_time is not None:
            dt = now - self.last_control_time

        self.last_control_time = now

        if dt > 0.0:
            self.yaw_integral += (error * dt)
            # Integral windup 제한
            self.yaw_integral = max(-0.5, min(0.5, self.yaw_integral))

        yaw_correction = (
            self.kp_yaw * error
            + self.ki_yaw * self.yaw_integral
            - self.kd_yaw * self.yaw_rate
        )

        yaw_correction = max(
            -self.max_yaw_correction,
            min(self.max_yaw_correction, yaw_correction))

        return yaw_correction

    def timer_callback(self):

        if self.shutdown_event.is_set() or self.finished:
            return
        # -----------------------------
        # 정지 명령 반복 전송
        # -----------------------------
        if self.stop_ticks > 0:

            self.publish_stop()
            self.stop_ticks -= 1

            if self.stop_ticks == 0:
                if self.interactive:
                    self.ready_event.set()
                else:
                    self.finished = True

            return

        # -----------------------------
        # 새로운 입력 확인
        # -----------------------------
        if not self.running:

            try:
                command = self.command_queue.get_nowait()

            except queue.Empty:
                if self.input_closed.is_set():
                    self.finished = True
                return

            self.start_trajectory(*command)
            return

        now = time.monotonic()

        # -----------------------------
        # IMU 초기값 대기
        # -----------------------------
        if self.start_time is None:

            if (
                self.wait_started_at is not None
                and now - self.wait_started_at > 3.0
            ):
                self.finish_trajectory(
                    'IMU timeout - trajectory cancelled'
                )

            return

        # -----------------------------
        # 주행 중 IMU 수신 확인
        # -----------------------------
        if self.heading_active:

            if (
                self.last_imu_time is None
                or now - self.last_imu_time > 0.5
            ):
                self.finish_trajectory(
                    'IMU data timeout - trajectory stopped'
                )
                return

        elapsed = now - self.start_time

        # -----------------------------
        # Trajectory 종료
        # -----------------------------
        if elapsed >= self.duration:

            self.finish_trajectory(
                'Trajectory finished'
            )
            return

        # -----------------------------
        # Twist 생성
        # -----------------------------
        msg = Twist()

        msg.linear.x = self.vx
        msg.linear.y = self.vy

        if self.heading_active:
            msg.angular.z = self.calculate_yaw_correction()
        else:
            msg.angular.z = self.yaw

        self.publisher.publish(msg)

    def finish_trajectory(self, message):

        self.publish_stop()

        self.running = False
        self.start_time = None
        self.wait_started_at = None

        self.heading_active = False
        self.target_yaw = None
        self.yaw_integral = 0.0
        self.last_control_time = None

        # 정지 명령 5회 추가 전송
        self.stop_ticks = 5

        self.get_logger().info(message)

    def publish_stop(self):

        msg = Twist()

        msg.linear.x = 0.0
        msg.linear.y = 0.0
        msg.angular.z = 0.0

        self.publisher.publish(msg)

    def stop_before_shutdown(self):
        # Stop callbacks and input before sending the final zero commands.
        self.shutdown_event.set()
        self.ready_event.set()
        self.timer.cancel()
        self.running = False
        self.heading_active = False
        self.finished = True
        for _ in range(5):
            if not rclpy.ok():
                break
            self.publish_stop()
            time.sleep(0.02)


def main(args=None):
    rclpy.init(args=args)
    node = None
    previous_handlers = {}

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    try:
        # Keep the ROS context alive until stop requests have been sent.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous_handlers[sig] = signal.signal(sig, interrupt)
        node = TimedTrajectory()
        while rclpy.ok() and not node.finished:
            rclpy.spin_once(
                node,
                timeout_sec=0.1
            )

    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().info('Trajectory interrupted')

    finally:
        for sig in previous_handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if node is not None:
                try:
                    node.stop_before_shutdown()
                finally:
                    node.destroy_node()
        finally:
            try:
                if rclpy.ok():
                    rclpy.shutdown()
            finally:
                for sig, handler in previous_handlers.items():
                    signal.signal(sig, handler)


if __name__ == '__main__':
    main()

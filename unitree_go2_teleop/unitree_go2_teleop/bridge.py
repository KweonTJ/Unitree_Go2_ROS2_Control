"""Convert keyboard Twist messages into official Unitree sport requests."""

import math
import signal
import time

import rclpy
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from unitree_api.msg import Request

from .control import Control, request_fields, ZERO_COMMAND

DEFAULT_PARAMETERS = {
    'input_topic': '/cmd_vel',
    'request_topic': '/api/sport/request',
    'max_linear': 0.3,
    'max_lateral': 0.3,
    'max_yaw': 0.4,
    # 'linear_accel': 0.25,
    # 'linear_decel': 0.45,
    # 'lateral_accel': 0.25,
    # 'lateral_decel': 0.45,
    # 'yaw_accel': 0.8,
    # 'yaw_decel': 1.0,
    'command_timeout': 1.0,
    'publish_rate': 50.0,
    'stop_duration': 0.5,
    'dry_run': False,
}
SHUTDOWN_STOP_COUNT = 5
SHUTDOWN_STOP_INTERVAL = 0.05
class SportBridge(Node):
    def __init__(self):
        super().__init__('go2_keyboard_bridge')
        params = self._read_parameters()
        rate = params['publish_rate']
        if not math.isfinite(rate) or not 1.0 <= rate <= 100.0:
            raise ValueError('publish_rate must be between 1 and 100 Hz')

        self.control = Control(
            max_linear=params['max_linear'],
            max_lateral=params['max_lateral'],
            max_yaw=params['max_yaw'],
            timeout=params['command_timeout'],
            stop_duration=params['stop_duration'],
            # linear_accel=params['linear_accel'],
            # linear_decel=params['linear_decel'],
            # lateral_accel=params['lateral_accel'],
            # lateral_decel=params['lateral_decel'],
            # yaw_accel=params['yaw_accel'],
            # yaw_decel=params['yaw_decel'],
        )
        self.dry_run = params['dry_run']
        self.last_log = None
        self.publisher = None
        if not self.dry_run:
            self.publisher = self.create_publisher(
                Request, params['request_topic'], 10
            )

        # 입력 큐에는 최신 명령 하나만 유지합니다.
        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
        )
        self.subscription = self.create_subscription(
            Twist, params['input_topic'], self.on_twist, qos
        )

        # /clock이 멈춰도 타임아웃 처리가 실행되도록 steady clock을 사용합니다.
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(
            1.0 / rate, self.tick, clock=self.steady_clock
        )
        self.get_logger().info(
            f"dry_run={self.dry_run} "
            f"input={params['input_topic']} output={params['request_topic']} "
            f"limits=({self.control.max_linear}, {self.control.max_lateral}) m/s, "
            f"{self.control.max_yaw} rad/s; "
            f"timeout={self.control.timeout} s; rate={rate} Hz"
        )

    def _read_parameters(self):
        """시작 시 파라미터를 선언하고 설정값을 가져옵니다."""
        params = {}
        for name, default in DEFAULT_PARAMETERS.items():
            self.declare_parameter(
                name, default, ParameterDescriptor(read_only=True)
            )
            params[name] = self.get_parameter(name).value
        return params

    def on_twist(self, msg):
        accepted = self.control.receive(
            (msg.linear.x, msg.linear.y, msg.linear.z),
            (msg.angular.x, msg.angular.y, msg.angular.z),
            time.monotonic(),
        )
        if not accepted:
            self.get_logger().warning(
                'Rejected non-finite or unsupported axes; stopping'
            )

        # 정지 입력과 잘못된 입력은 다음 타이머를 기다리지 않습니다.
        if self.control.stop_requested:
            self.send(ZERO_COMMAND, stop=True)

    def tick(self):
        command = self.control.sample(time.monotonic())
        if command is not None:
            self.send(command, stop=self.control.stop_requested)

    def send(self, command, *, stop=False):
        api_id, parameter = request_fields(command, stop=stop)
        if self.dry_run:
            if (api_id, parameter) != self.last_log:
                self.get_logger().info(
                    f'DRY RUN api_id={api_id} parameter={parameter}'
                )
                self.last_log = (api_id, parameter)
            return

        request = Request()
        request.header.identity.api_id = api_id
        request.parameter = parameter
        self.publisher.publish(request)

    def stop_before_shutdown(self):
        """ROS context가 살아 있는 동안 종료 전 정지를 시도합니다."""
        self.timer.cancel()
        if not self.control.active:
            return

        self.control.stop(time.monotonic())
        for _ in range(SHUTDOWN_STOP_COUNT):
            if not rclpy.ok():
                break
            self.send(ZERO_COMMAND, stop=True)
            time.sleep(SHUTDOWN_STOP_INTERVAL)

def main(args=None):
    rclpy.init(args=args)
    node = None
    previous_handlers = {}

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    try:
        # 정지 요청을 보내기 전에 ROS context가 종료되지 않도록 합니다.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous_handlers[sig] = signal.signal(sig, interrupt)
        node = SportBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
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


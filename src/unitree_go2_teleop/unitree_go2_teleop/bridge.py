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

from .control import Control, request_fields


class SportBridge(Node):
    def __init__(self):
        super().__init__('go2_keyboard_bridge')
        defaults = {
            'input_topic': '/go2_teleop/cmd_vel',
            'request_topic': '/api/sport/request',
            'max_linear': 0.2,
            'max_yaw': 0.4,
            'command_timeout': 0.5,
            'publish_rate': 20.0,
            'stop_duration': 0.5,
            'dry_run': True,
        }
        for name, value in defaults.items():
            self.declare_parameter(name, value, ParameterDescriptor(read_only=True))
        value = lambda name: self.get_parameter(name).value
        self.control = Control(value('max_linear'), value('max_yaw'),
                               value('command_timeout'), value('stop_duration'))
        rate = value('publish_rate')
        if not math.isfinite(rate) or not 1.0 <= rate <= 100.0:
            raise ValueError('publish_rate must be between 1 and 100 Hz')
        self.dry_run = value('dry_run')
        self.last_log = None
        self.publisher = None
        if not self.dry_run:
            self.publisher = self.create_publisher(Request, value('request_topic'), 10)
        # Keep only the newest keyboard command; never replay a queue of old keys.
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.VOLATILE)
        self.subscription = self.create_subscription(
            Twist, value('input_topic'), self.on_twist, qos)
        # Watchdog must still run if use_sim_time is set without a /clock source.
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(1.0 / rate, self.tick, clock=self.steady_clock)
        self.get_logger().info(
            'dry_run={} input={} output={} limits={} m/s, {} rad/s; timeout={} s'.format(
                self.dry_run, value('input_topic'), value('request_topic'),
                self.control.max_linear, self.control.max_yaw, self.control.timeout))

    def on_twist(self, msg):
        accepted = self.control.receive(
            (msg.linear.x, msg.linear.y, msg.linear.z),
            (msg.angular.x, msg.angular.y, msg.angular.z), time.monotonic())
        if not accepted:
            self.get_logger().warning('Rejected non-finite or unsupported axes; stopping')
        self.tick()

    def tick(self):
        command = self.control.sample(time.monotonic())
        if command is not None:
            self.send(command)

    def send(self, command):
        api_id, parameter = request_fields(command)
        if self.dry_run:
            if (api_id, parameter) != self.last_log:
                self.get_logger().info('DRY RUN api_id={} parameter={}'.format(api_id, parameter))
                self.last_log = (api_id, parameter)
            return
        request = Request()
        request.header.identity.api_id = api_id
        request.parameter = parameter
        self.publisher.publish(request)

    def stop_before_shutdown(self):
        if not self.control.active:
            return
        # Best effort only: process kill, power loss, or DDS failure cannot be covered.
        for _ in range(5):
            if not rclpy.ok():
                break
            self.send((0.0, 0.0))
            time.sleep(0.05)


def main(args=None):
    rclpy.init(args=args)
    node = None
    previous = {}

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    try:
        # Keep the ROS context alive while sending shutdown stop requests.
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[sig] = signal.signal(sig, interrupt)
        node = SportBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        try:
            if node is not None:
                node.stop_before_shutdown()
                node.destroy_node()
            if rclpy.ok():
                rclpy.shutdown()
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)

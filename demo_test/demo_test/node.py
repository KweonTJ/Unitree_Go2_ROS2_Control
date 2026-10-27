"""Publish circle commands, stopping for front lidar returns."""

import signal
import time

import rclpy
from geometry_msgs.msg import Twist
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2

from .control import CircleControl, DEFAULTS


class CircleNode(Node):
    def __init__(self):
        super().__init__('circle_test')
        params = dict(DEFAULTS, lidar_topic='/utlidar/cloud',
                      lidar_frame='utlidar_lidar', output_topic='/cmd_vel')
        for name, value in params.items():
            self.declare_parameter(name, value, ParameterDescriptor(read_only=True))
            params[name] = self.get_parameter(name).value
        self.control = CircleControl(**{k: params[k] for k in DEFAULTS})
        self.frame = params['lidar_frame']
        if not self.frame:
            raise ValueError('lidar_frame must name a robot-aligned lidar frame')
        self.publisher = self.create_publisher(Twist, params['output_topic'], 1)
        self.subscription = self.create_subscription(
            PointCloud2, params['lidar_topic'], self.on_cloud, qos_profile_sensor_data)
        self.clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(
            1.0 / params['publish_rate'], self.tick, clock=self.clock)
        self.last_command = None
        self.get_logger().info('Waiting for fresh lidar data in frame ' + self.frame)

    def on_cloud(self, msg):
        try:
            if msg.header.frame_id != self.frame:
                raise ValueError('Expected frame ' + self.frame + ', got ' + msg.header.frame_id)
            points = point_cloud2.read_points(
                msg, field_names=('x', 'y', 'z'), skip_nans=False)
            self.control.observe(points, time.monotonic())
        except Exception as exc:
            self.control.invalidate()
            self.get_logger().error('Invalid lidar input: ' + str(exc))
        self.tick()

    def tick(self):
        command = self.control.command(time.monotonic())
        self.publish(command)
        if command != self.last_command:
            self.get_logger().info('CIRCLE' if command != (0.0, 0.0) else 'STOP')
            self.last_command = command

    def publish(self, command):
        msg = Twist()
        msg.linear.x, msg.angular.z = command
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = None
    handlers = {}

    def interrupt(signum, frame):
        raise KeyboardInterrupt

    try:
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            handlers[sig] = signal.signal(sig, interrupt)
        node = CircleNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        for sig in handlers:
            signal.signal(sig, signal.SIG_IGN)
        if node is not None:
            node.timer.cancel()
            if rclpy.ok():
                for _ in range(5):
                    node.publish((0.0, 0.0))
                    time.sleep(0.05)
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in handlers.items():
            signal.signal(sig, handler)

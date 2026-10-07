#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class TimedTrajectory(Node):

    def __init__(self):
        super().__init__('timed_trajectory')

        # -----------------------------
        # ROS2 Parameters
        # -----------------------------
        self.declare_parameter('output_topic', '/cmd_vel')

        self.declare_parameter('vx', 0.0)
        self.declare_parameter('vy', 0.0)
        self.declare_parameter('yaw', 0.0)

        self.declare_parameter('duration', 5.0)
        self.declare_parameter('publish_rate', 50.0)

        # -----------------------------
        # Parameter values
        # -----------------------------
        self.output_topic = self.get_parameter(
            'output_topic'
        ).value

        self.vx = float(
            self.get_parameter('vx').value
        )

        self.vy = float(
            self.get_parameter('vy').value
        )

        self.yaw = float(
            self.get_parameter('yaw').value
        )

        self.duration = float(
            self.get_parameter('duration').value
        )

        self.publish_rate = float(
            self.get_parameter('publish_rate').value
        )

        # -----------------------------
        # Publisher
        # -----------------------------
        self.publisher = self.create_publisher(
            Twist,
            self.output_topic,
            10
        )

        # 시작 시간
        self.start_time = time.monotonic()

        self.finished = False

        # -----------------------------
        # Timer
        # -----------------------------
        self.timer = self.create_timer(
            1.0 / self.publish_rate,
            self.timer_callback
        )

        self.get_logger().info(
            f'Start trajectory | '
            f'vx={self.vx:.2f} m/s, '
            f'vy={self.vy:.2f} m/s, '
            f'yaw={self.yaw:.2f} rad/s, '
            f'duration={self.duration:.2f} s'
        )

    def timer_callback(self):

        elapsed = time.monotonic() - self.start_time

        # -----------------------------
        # 주행 종료
        # -----------------------------
        if elapsed >= self.duration:

            self.publish_stop()

            self.get_logger().info(
                'Trajectory finished'
            )

            self.finished = True

            self.timer.cancel()

            return

        # -----------------------------
        # 주행 명령
        # -----------------------------
        msg = Twist()

        msg.linear.x = self.vx
        msg.linear.y = self.vy

        msg.angular.z = self.yaw

        self.publisher.publish(msg)

    def publish_stop(self):

        msg = Twist()

        msg.linear.x = 0.0
        msg.linear.y = 0.0
        msg.angular.z = 0.0

        self.publisher.publish(msg)


def main(args=None):

    rclpy.init(args=args)

    node = TimedTrajectory()

    try:

        while rclpy.ok() and not node.finished:

            rclpy.spin_once(
                node,
                timeout_sec=0.1
            )

    except KeyboardInterrupt:

        node.get_logger().info(
            'Trajectory interrupted'
        )

    finally:

        # Ctrl+C 또는 정상 종료 시 정지 명령 반복
        for _ in range(5):

            node.publish_stop()

            rclpy.spin_once(
                node,
                timeout_sec=0.02
            )

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
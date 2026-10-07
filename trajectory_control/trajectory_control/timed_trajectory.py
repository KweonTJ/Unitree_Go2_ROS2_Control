#!/usr/bin/env python3

import time
import math
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import Twist
from unitree_go.msg import LowState

def wrap_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))
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

        # 시작 시간
        # self.start_time = time.monotonic()
        self.heading_active = (
            self.heading_control
            and abs(self.yaw) < 1e-6
        )
                
        if self.heading_active:
            self.start_time = None
        else:
            self.start_time = time.monotonic()

        self.finished = False
        self.current_yaw = None
        self.yaw_rate = 0.0
        self.target_yaw = None
        self.yaw_integral = 0.0
        self.last_control_time = None

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

    def lowstate_callback(self, msg):

        yaw = float(
            msg.imu_state.rpy[2]
        )

        yaw_rate = float(
            msg.imu_state.gyroscope[2]
        )

        if not (
            math.isfinite(yaw)
            and math.isfinite(yaw_rate)
        ):
            return

        self.current_yaw = yaw
        self.yaw_rate = yaw_rate

        # 최초 방향을 목표 방향으로 설정
        if (
            self.heading_active
            and self.target_yaw is None
        ):
            self.target_yaw = yaw

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

                self.yaw_integral += (
                    error * dt
                )

                # Integral windup 제한
                self.yaw_integral = max(
                    -0.5,
                    min(
                        0.5,
                        self.yaw_integral
                    )
                )

            yaw_correction = (
                self.kp_yaw * error
                + self.ki_yaw * self.yaw_integral
                - self.kd_yaw * self.yaw_rate
            )

            yaw_correction = max(
                -self.max_yaw_correction,
                min(
                    self.max_yaw_correction,
                    yaw_correction
                )
            )

            return yaw_correction

    def timer_callback(self):

        #elapsed = time.monotonic() - self.start_time
        if self.start_time is None:
            return

        elapsed = (
            time.monotonic()
            - self.start_time
        )

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
        if self.heading_active:
            msg.angular.z = (
                self.calculate_yaw_correction()
            )

        else:
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
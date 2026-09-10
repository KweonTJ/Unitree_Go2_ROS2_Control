"""Opt-in DDS tests: run only with the documented loopback/domain isolation."""

import json
import os
import signal
import subprocess
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('GO2_TELEOP_ROS_TEST') != '1', reason='ROS integration tests are opt-in')


@pytest.fixture(autouse=True)
def cleanup_failed_initialization():
    yield
    import rclpy
    if rclpy.ok():
        rclpy.shutdown()


def spin_until(executor, condition, timeout=4.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        executor.spin_once(timeout_sec=0.02)
        if condition():
            return
    assert condition(), 'DDS test condition timed out'


@pytest.mark.parametrize('dry_run', [True, False])
def test_ros_round_trip_and_watchdog_with_paused_sim_time(dry_run):
    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.executors import SingleThreadedExecutor
    from unitree_api.msg import Request
    from unitree_go2_teleop.bridge import SportBridge

    rclpy.init(args=['--ros-args', '-p', 'dry_run:=' + str(dry_run).lower(),
                    '-p', 'request_topic:=/go2_teleop_test/request',
                    '-p', 'use_sim_time:=true'])
    bridge = SportBridge()
    peer = rclpy.create_node('go2_teleop_test_peer')
    publisher = peer.create_publisher(Twist, '/go2_teleop/cmd_vel', 10)
    received = []
    subscription = peer.create_subscription(
        Request, '/go2_teleop_test/request', received.append, 10)
    executor = SingleThreadedExecutor()
    executor.add_node(bridge)
    executor.add_node(peer)
    try:
        spin_until(executor, lambda: publisher.get_subscription_count() > 0)
        if not dry_run:
            spin_until(executor, lambda: bridge.publisher.get_subscription_count() > 0)
        assert received == []  # Startup must never command the robot.
        command = Twist()
        command.linear.x = 3.0
        command.angular.z = -3.0
        publisher.publish(command)
        if dry_run:
            spin_until(executor, lambda: bridge.last_log is not None)
            assert bridge.publisher is None
            assert bridge.last_log[0] == 1008
            spin_until(executor, lambda: bridge.last_log[0] == 1003)
            assert received == []
        else:
            spin_until(executor, lambda: any(x.header.identity.api_id == 1008 for x in received))
            move = next(x for x in received if x.header.identity.api_id == 1008)
            assert json.loads(move.parameter) == {'x': 0.2, 'y': 0.0, 'z': -0.4}
            spin_until(executor, lambda: any(x.header.identity.api_id == 1003 for x in received))
            stop_index = next(i for i, x in enumerate(received) if x.header.identity.api_id == 1003)
            spin_until(executor, lambda: not bridge.control.active)
            assert all(x.header.identity.api_id == 1003 for x in received[stop_index:])
    finally:
        executor.shutdown()
        peer.destroy_node()
        bridge.destroy_node()
        rclpy.shutdown()


def test_process_sigterm_sends_stop():
    import rclpy
    from geometry_msgs.msg import Twist
    from rclpy.executors import SingleThreadedExecutor
    from unitree_api.msg import Request

    rclpy.init(args=[])
    peer = rclpy.create_node('go2_shutdown_test_peer')
    publisher = peer.create_publisher(Twist, '/go2_shutdown_test/cmd_vel', 10)
    received = []
    subscription = peer.create_subscription(
        Request, '/go2_shutdown_test/request', received.append, 10)
    executor = SingleThreadedExecutor()
    executor.add_node(peer)
    process = subprocess.Popen([
        sys.executable, '-c', 'from unitree_go2_teleop.bridge import main; main()',
        '--ros-args', '-p', 'dry_run:=false',
        '-p', 'input_topic:=/go2_shutdown_test/cmd_vel',
        '-p', 'request_topic:=/go2_shutdown_test/request',
        '-p', 'command_timeout:=5.0',
    ])
    try:
        spin_until(executor, lambda: publisher.get_subscription_count() > 0)
        spin_until(executor, lambda: peer.count_publishers('/go2_shutdown_test/request') > 0)
        command = Twist()
        command.linear.x = 0.1
        publisher.publish(command)
        spin_until(executor, lambda: any(x.header.identity.api_id == 1008 for x in received))
        received.clear()
        process.send_signal(signal.SIGTERM)
        spin_until(executor, lambda: any(x.header.identity.api_id == 1003 for x in received), 2.0)
        assert process.wait(timeout=3.0) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3.0)
        executor.shutdown()
        peer.destroy_node()
        rclpy.shutdown()

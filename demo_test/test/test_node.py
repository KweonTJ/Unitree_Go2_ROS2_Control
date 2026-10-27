"""Check ROS message callbacks without DDS or robot requests."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip('rclpy')
pytest.importorskip('sensor_msgs_py')

from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header

from demo_test import node as demo_node
from demo_test.control import CircleControl


@pytest.fixture
def node(monkeypatch):
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(demo_node, 'time', SimpleNamespace(monotonic=lambda: clock.now))
    outputs = []
    n = SimpleNamespace(
        control=CircleControl(), frame='utlidar_lidar',
        publisher=SimpleNamespace(publish=outputs.append),
        last_command=None, get_logger=lambda: SimpleNamespace(info=Mock(), error=Mock()),
    )
    n.publish = lambda command: demo_node.CircleNode.publish(n, command)
    n.tick = lambda: demo_node.CircleNode.tick(n)
    n.cloud = lambda msg: demo_node.CircleNode.on_cloud(n, msg)
    n.outputs = outputs
    n.clock = clock
    return n


def cloud(distance, frame='utlidar_lidar'):
    header = Header()
    header.frame_id = frame
    return point_cloud2.create_cloud_xyz32(header, [(distance, 0.0, 0.0)])


def command(n):
    msg = n.outputs[-1]
    return (msg.linear.x, msg.linear.y, msg.linear.z,
            msg.angular.x, msg.angular.y, msg.angular.z)


def test_first_timer_drives_then_cloud_stops_and_resumes(node):
    node.tick()
    assert command(node) == (0.3, 0, 0, 0, 0, 0.3)
    node.clock.now = 0.1
    node.cloud(cloud(3.0))
    assert command(node) == (0.3, 0, 0, 0, 0, 0.3)
    node.clock.now = 0.2
    node.cloud(cloud(0.8))
    assert command(node) == (0, 0, 0, 0, 0, 0)
    node.clock.now = 0.3
    node.cloud(cloud(3.0))
    assert command(node) == (0, 0, 0, 0, 0, 0)
    node.clock.now = 0.6
    node.cloud(cloud(3.0))
    node.clock.now = 0.81
    node.tick()
    assert command(node) == (0.3, 0, 0, 0, 0, 0.3)
    node.clock.now = 1.11
    node.tick()
    assert command(node) == (0, 0, 0, 0, 0, 0)


def test_bad_frame_stays_stopped_after_immediate_start(node):
    node.tick()
    assert command(node) == (0.3, 0, 0, 0, 0, 0.3)
    node.cloud(cloud(3.0, frame='odom'))
    assert command(node) == (0, 0, 0, 0, 0, 0)
    node.clock.now = 10
    node.tick()
    assert command(node) == (0, 0, 0, 0, 0, 0)

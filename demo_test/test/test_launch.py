"""Verify demo limits reach the existing bridge without sending robot commands."""

import json
from pathlib import Path
import runpy

import pytest

pytest.importorskip('launch_ros')

import launch_ros.actions
from launch import LaunchContext, LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetLaunchConfiguration
from launch_ros.utilities import evaluate_parameters, normalize_parameters
from unitree_go2_teleop.control import Control, MOVE, STOP, request_fields

from demo_test.control import CircleControl


@pytest.mark.parametrize('filename,yaw,node_name', [
    ('circle_test.launch.py', 0.3, 'circle_test'),
    ('straight_test.launch.py', 0.0, 'straight_test'),
])
def test_launch_bridge_preserves_max_speed_and_obstacle_stop(
        tmp_path, monkeypatch, filename, yaw, node_name):
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path))
    nodes = []
    original = launch_ros.actions.Node

    def capture_node(**kwargs):
        nodes.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(launch_ros.actions, 'Node', capture_node)
    launch_file = Path(__file__).resolve().parents[1] / 'launch' / filename
    description = runpy.run_path(str(launch_file))['generate_launch_description']()
    context = LaunchContext()
    context.launch_configurations['vx'] = '0.5'

    def configure(action):
        # Resolve launch defaults/includes without executing a Node or any DDS.
        if isinstance(action, LaunchDescription):
            for child in action.entities:
                configure(child)
        elif isinstance(action, IncludeLaunchDescription):
            for child in action.execute(context):
                configure(child)
        elif isinstance(action, (DeclareLaunchArgument, SetLaunchConfiguration)):
            action.execute(context)

    configure(description)
    controller = next(n for n in nodes if n['package'] == 'demo_test')
    params = evaluate_parameters(context, normalize_parameters(controller['parameters']))[0]
    assert params['vx'] == 0.5 and params['yaw'] == yaw
    assert controller['name'].perform(context) == node_name
    bridge_args = next(n['parameters'][0] for n in nodes
                       if n['package'] == 'unitree_go2_teleop')
    assert bridge_args['max_linear'] == 0.5
    bridge = Control(max_linear=bridge_args['max_linear'])
    circle = CircleControl(vx=params['vx'], yaw=params['yaw'])
    for now, points, expected in [
            (0.0, None, (0.5, 0.0, yaw)),
            (0.1, [(0.8, 0, 0)], (0.0, 0.0, 0.0)),
            (0.2, [(3.0, 0, 0)], (0.0, 0.0, 0.0)),
            (0.5, [(3.0, 0, 0)], (0.0, 0.0, 0.0)),
            (0.71, None, (0.5, 0.0, yaw))]:
        if points is not None:
            circle.observe(points, now)
        vx, yaw = circle.command(now)
        assert bridge.receive((vx, 0.0, 0.0), (0.0, 0.0, yaw), now)
        command = bridge.sample(now)
        assert command == expected
        api, payload = request_fields(command, stop=bridge.stop_requested)
        if vx:
            assert api == MOVE and json.loads(payload)['x'] == 0.5
        else:
            assert api == STOP

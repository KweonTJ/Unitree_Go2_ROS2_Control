"""Exercise control and shutdown without starting DDS or sending robot requests."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


SOURCE = Path(__file__).resolve().parents[1]


class Twist:
    def __init__(self):
        self.linear = SimpleNamespace(x=0.0, y=0.0, z=0.0)
        self.angular = SimpleNamespace(x=0.0, y=0.0, z=0.0)


@pytest.fixture
def controller(monkeypatch):
    overrides = {}
    clock = SimpleNamespace(now=100.0)
    context = SimpleNamespace(active=True)

    class Node:
        def __init__(self, name):
            self.params = {}
            self.outputs = []
            self.destroy_node = Mock()

        def declare_parameter(self, name, value):
            self.params[name] = overrides.get(name, value)

        def get_parameter(self, name):
            return SimpleNamespace(value=self.params[name])

        def create_publisher(self, *args):
            return SimpleNamespace(publish=self.outputs.append)

        def create_subscription(self, *args):
            return None

        def create_timer(self, *args, **kwargs):
            return SimpleNamespace(cancel=Mock())

        def get_logger(self):
            return SimpleNamespace(info=Mock())

    def shutdown():
        context.active = False

    ros = SimpleNamespace(
        init=Mock(), ok=lambda: context.active,
        shutdown=Mock(side_effect=shutdown), spin_once=Mock(),
    )
    modules = {
        'rclpy': ros,
        'rclpy.node': SimpleNamespace(Node=Node),
        'rclpy.clock': SimpleNamespace(
            Clock=lambda **kwargs: object(),
            ClockType=SimpleNamespace(STEADY_TIME=1)),
        'rclpy.qos': SimpleNamespace(qos_profile_sensor_data=object()),
        'geometry_msgs.msg': SimpleNamespace(Twist=Twist),
        'unitree_go.msg': SimpleNamespace(LowState=object),
    }
    for name, module in modules.items():
        monkeypatch.setitem(__import__('sys').modules, name, module)
    spec = importlib.util.spec_from_file_location(
        'trajectory_under_test', SOURCE / 'trajectory_control/timed_trajectory.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.time = SimpleNamespace(monotonic=lambda: clock.now, sleep=Mock())
    module.threading = SimpleNamespace(
        Event=__import__('threading').Event, Thread=Mock())
    module.signal = SimpleNamespace(
        SIGINT=2, SIGTERM=15, SIGHUP=1, SIG_IGN=0, signal=Mock(return_value='old'))
    return SimpleNamespace(module=module, overrides=overrides, clock=clock, ros=ros)


def imu(yaw=0.0, rate=0.0):
    return SimpleNamespace(imu_state=SimpleNamespace(
        rpy=[0.0, 0.0, yaw], gyroscope=[0.0, 0.0, rate]))


def is_stop(message):
    return (message.linear.x, message.linear.y, message.angular.z) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize('name,value', [
    ('publish_rate', 0.0), ('publish_rate', -1.0), ('publish_rate', 2.0),
    ('publish_rate', 101.0), ('publish_rate', float('inf')),
    ('duration', 0.0), ('duration', float('nan')),
    ('vx', 0.31), ('vy', -0.31), ('yaw', 0.41), ('vx', float('inf')),
    ('kp_yaw', -1.0), ('ki_yaw', float('inf')), ('kd_yaw', float('nan')),
    ('max_yaw_correction', -0.15), ('max_yaw_correction', 0.41),
    ('max_yaw_correction', float('nan')),
])
def test_rejects_invalid_parameters(controller, name, value):
    controller.overrides[name] = value
    with pytest.raises(ValueError):
        controller.module.TimedTrajectory()


def test_interactive_waits_for_input_and_accepts_next_run(controller):
    node = controller.module.TimedTrajectory()
    node.timer_callback()
    assert not node.finished and not node.running and node.outputs == []
    node.ready_event.clear()
    node.command_queue.put((0.3, 0.0, 0.2, 1.0))
    node.timer_callback()
    node.timer_callback()
    assert node.outputs[-1].linear.x == 0.3
    controller.clock.now += 1.0
    node.timer_callback()
    assert not node.ready_event.is_set()
    for _ in range(5):
        node.timer_callback()
    assert node.ready_event.is_set() and not node.finished
    assert all(is_stop(m) for m in node.outputs[-6:])
    node.command_queue.put((0.0, -0.3, 0.2, 1.0))
    node.timer_callback()
    node.timer_callback()
    assert node.outputs[-1].linear.y == -0.3


def test_single_run_uses_parameters_and_exits_after_stops(controller):
    controller.overrides.update(interactive=False, vx=0.3, duration=1.0)
    node = controller.module.TimedTrajectory()
    assert node.input_thread is None
    node.timer_callback()
    assert node.outputs == []
    node.lowstate_callback(imu())
    node.timer_callback()
    assert node.outputs[-1].linear.x == 0.3
    controller.clock.now += 1.0
    node.lowstate_callback(imu())
    node.timer_callback()
    assert not node.finished
    for _ in range(5):
        node.timer_callback()
    assert node.finished and all(is_stop(m) for m in node.outputs[-6:])


@pytest.mark.parametrize('started', [False, True])
def test_imu_timeout_stops(controller, started):
    node = controller.module.TimedTrajectory()
    node.start_trajectory(0.3, 0.0, 0.0, 5.0)
    if started:
        node.lowstate_callback(imu())
    controller.clock.now += 0.51 if started else 3.01
    node.timer_callback()
    assert not node.running and is_stop(node.outputs[-1])


def test_new_run_waits_for_fresh_heading(controller):
    node = controller.module.TimedTrajectory()
    node.lowstate_callback(imu(yaw=1.0))
    node.start_trajectory(0.3, 0.0, 0.0, 5.0)
    node.timer_callback()
    assert node.outputs == [] and node.target_yaw is None
    node.lowstate_callback(imu(yaw=2.0))
    node.timer_callback()
    assert node.target_yaw == 2.0 and node.outputs[-1].angular.z == 0.0


def test_heading_correction_sign_and_limit(controller):
    node = controller.module.TimedTrajectory()
    node.start_trajectory(0.3, 0.0, 0.0, 5.0)
    node.lowstate_callback(imu())
    node.lowstate_callback(imu(yaw=0.3))
    assert node.calculate_yaw_correction() == -0.15
    node.lowstate_callback(imu(yaw=-0.3))
    assert node.calculate_yaw_correction() == 0.15


def test_shutdown_blocks_due_timer_and_queued_motion(controller):
    node = controller.module.TimedTrajectory()
    node.start_trajectory(0.3, 0.0, 0.2, 5.0)
    node.command_queue.put((0.3, 0.0, 0.2, 5.0))
    # Even a callback already scheduled when shutdown begins cannot move.
    controller.module.time.sleep.side_effect = lambda _: node.timer_callback()
    node.stop_before_shutdown()
    node.timer.cancel.assert_called_once()
    assert len(node.outputs) == 5 and all(is_stop(m) for m in node.outputs)
    assert node.finished and not node.running and node.shutdown_event.is_set()


def test_main_interrupt_stops_before_context_shutdown(controller, monkeypatch):
    node = controller.module.TimedTrajectory()
    node.start_trajectory(0.3, 0.0, 0.2, 5.0)
    monkeypatch.setattr(controller.module, 'TimedTrajectory', lambda: node)
    controller.ros.spin_once.side_effect = KeyboardInterrupt
    controller.module.main()
    assert len(node.outputs) == 5 and all(is_stop(m) for m in node.outputs)
    node.destroy_node.assert_called_once()
    controller.ros.shutdown.assert_called_once()
    assert controller.ros.spin_once.call_count == 1
    assert controller.module.signal.signal.call_args_list[-1].args == (1, 'old')


def test_main_initialization_failure_cleans_context(controller):
    controller.overrides['publish_rate'] = 0.0
    with pytest.raises(ValueError):
        controller.module.main()
    controller.ros.shutdown.assert_called_once()


def test_eof_finishes_idle_interactive_node(controller, monkeypatch):
    node = controller.module.TimedTrajectory()
    monkeypatch.setattr('builtins.input', Mock(side_effect=EOFError))
    node.input_loop()
    node.timer_callback()
    assert node.finished


def test_launch_generates_both_exclusive_modes(tmp_path, monkeypatch):
    monkeypatch.setenv('ROS_LOG_DIR', str(tmp_path))
    launch = pytest.importorskip('launch')
    pytest.importorskip('launch_ros')
    import runpy
    from launch.actions import TimerAction
    description = runpy.run_path(str(SOURCE / 'launch/timed_trajectory.launch.py'))[
        'generate_launch_description']()
    delayed = next(x for x in description.entities if isinstance(x, TimerAction))
    for value, expected in [('true', [True, False]), ('false', [False, True])]:
        context = launch.LaunchContext()
        context.launch_configurations['interactive'] = value
        assert [x.condition.evaluate(context) for x in delayed.actions] == expected

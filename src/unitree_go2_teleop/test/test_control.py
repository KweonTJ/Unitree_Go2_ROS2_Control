import json

import pytest

from unitree_go2_teleop.control import Control, MOVE, STOP, request_fields


@pytest.mark.parametrize('vx,yaw', [
    (0.1, 0.0), (-0.1, 0.0), (0.0, 0.3), (0.0, -0.3),
    (0.1, 0.3), (0.1, -0.3), (-0.1, 0.3), (-0.1, -0.3),
])
def test_driving_directions_and_wire_format(vx, yaw):
    control = Control()
    control.receive((vx, 0.0, 0.0), (0.0, 0.0, yaw), 10.0)
    api, parameter = request_fields(control.sample(10.1))
    assert api == MOVE
    assert json.loads(parameter) == {'x': vx, 'y': 0.0, 'z': yaw}


def test_limits_in_both_directions():
    control = Control()
    for direction in [-1, 1]:
        control.receive((direction * 4.0, 0.0, 0.0), (0.0, 0.0, direction * 5.0), 0.0)
        assert control.sample(0.0) == (direction * 0.2, direction * 0.4)


def test_idle_timeout_stop_burst_and_rearm():
    control = Control()
    assert control.sample(0.0) is None
    control.receive((0.2, 0.0, 0.0), (0.0, 0.0, 0.4), 1.0)
    assert control.sample(1.49) == (0.2, 0.4)
    assert request_fields(control.sample(1.5)) == (STOP, '')
    assert control.sample(1.99) == (0.0, 0.0)
    assert control.sample(2.0) is None
    control.receive((-0.1, 0.0, 0.0), (0.0, 0.0, 0.0), 3.0)
    assert control.sample(3.1) == (-0.1, 0.0)


def test_new_input_refreshes_deadline_and_zero_stops_immediately():
    control = Control()
    control.receive((0.2, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0)
    control.receive((0.1, 0.0, 0.0), (0.0, 0.0, -0.2), 0.4)
    assert control.sample(0.6) == (0.1, -0.2)
    control.receive((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.7)
    assert request_fields(control.sample(0.7)) == (STOP, '')


@pytest.mark.parametrize('axis', range(6))
@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), -float('inf')])
def test_invalid_input_cancels_motion(axis, invalid):
    control = Control()
    control.receive((0.2, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0)
    values = [0.1, 0.0, 0.0, 0.0, 0.0, 0.2]
    values[axis] = invalid
    assert not control.receive(values[:3], values[3:], 0.1)
    assert request_fields(control.sample(0.1)) == (STOP, '')


@pytest.mark.parametrize('axis', [1, 2, 3, 4])
def test_unsupported_axes_stop(axis):
    values = [0.1, 0.0, 0.0, 0.0, 0.0, 0.2]
    values[axis] = 0.3
    control = Control()
    assert not control.receive(values[:3], values[3:], 0.0)
    assert control.sample(0.0) == (0.0, 0.0)


@pytest.mark.parametrize('name', ['max_linear', 'max_yaw', 'timeout', 'stop_duration'])
@pytest.mark.parametrize('value', [0.0, -1.0, float('nan'), float('inf')])
def test_bad_configuration_fails(name, value):
    with pytest.raises(ValueError):
        Control(**{name: value})

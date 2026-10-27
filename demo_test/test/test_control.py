import math

import pytest

from demo_test.control import CircleControl


CLEAR = [(3.0, 0.0, 0.0)]


def test_circle_stop_hold_and_resume():
    c = CircleControl()
    assert c.command(0) == (0, 0)
    c.observe(CLEAR, 0)
    c.observe(CLEAR, 0.3)
    assert c.command(0.5) == (0.3, 0.3)
    c.observe([(0.8, 0, 0)], 0.6)
    assert c.command(0.6) == (0, 0)
    c.observe([(0.8, 0, 0)], 1.0)
    assert c.command(1.0) == (0, 0)
    c.observe(CLEAR, 1.1)
    c.observe(CLEAR, 1.4)
    assert c.command(1.5) == (0, 0)
    assert c.command(1.61) == (0.3, 0.3)


def test_timeout_resets_clear_period_even_between_callbacks():
    c = CircleControl()
    c.observe(CLEAR, 0)
    c.observe(CLEAR, 0.3)
    assert c.command(0.5) == (0.3, 0.3)
    c.observe(CLEAR, 2)
    assert c.command(2) == (0, 0)
    c.observe(CLEAR, 2.3)
    assert c.command(2.6) == (0.3, 0.3)
    assert c.command(3) == (0, 0)


@pytest.mark.parametrize('points', [[], [(math.nan, 0, 0)], [(0, 0, 0)]])
def test_invalid_cloud_stops(points):
    c = CircleControl(clear_duration=0)
    c.observe(CLEAR, 0)
    assert c.command(0) == (0.3, 0.3)
    c.observe(points, 0.1)
    assert c.command(0.1) == (0, 0)


@pytest.mark.parametrize('point', [(-0.5, 0, 0), (0.1, 0.9, 0), (0.5, 0, -0.3),
                                  (0.5, 0, 0.6), (1.01, 0, 0)])
def test_front_roi(point):
    c = CircleControl(clear_duration=0)
    c.observe([point], 0)
    assert c.command(0) == (0.3, 0.3)
    c.observe([(1.0, 0, 0)], 0.1)
    assert c.command(0.1) == (0, 0)


@pytest.mark.parametrize('settings', [dict(vx=math.nan), dict(yaw=0), dict(vx=0.31),
                                    dict(lidar_timeout=0), dict(front_angle_deg=181),
                                    dict(min_height=1), dict(clear_duration=-1)])
def test_reject_invalid_settings(settings):
    with pytest.raises(ValueError):
        CircleControl(**settings)

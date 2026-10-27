import math

import pytest

from demo_test.control import CircleControl


CLEAR = [(3.0, 0.0, 0.0)]


def test_starts_driving_without_lidar_input():
    c = CircleControl()
    assert c.command(0) == (0.3, 0.3)
    # No startup timeout or clear delay before the first lidar message.
    assert c.command(10) == (0.3, 0.3)


def test_first_clear_scan_does_not_interrupt_driving():
    c = CircleControl()
    c.observe(CLEAR, 10)
    assert c.command(10) == (0.3, 0.3)
    assert c.command(10.2) == (0.3, 0.3)


def test_circle_stop_hold_and_resume():
    c = CircleControl()
    assert c.command(0) == (0.3, 0.3)
    # The first scan can itself detect an object and stop the ongoing motion.
    c.observe([(0.8, 0, 0)], 0.6)
    assert c.command(0.6) == (0, 0)
    c.observe([(0.8, 0, 0)], 1.0)
    assert c.command(1.0) == (0, 0)
    c.observe(CLEAR, 1.1)
    c.observe(CLEAR, 1.4)
    assert c.command(1.5) == (0, 0)
    assert c.command(1.61) == (0.3, 0.3)
    c.observe([(0.8, 0, 0)], 1.7)
    assert c.command(1.7) == (0, 0)


def test_invalid_input_is_not_treated_as_initial_lidar_wait():
    c = CircleControl()
    c.invalidate()
    assert c.command(0) == (0, 0)
    assert c.command(10) == (0, 0)
    c.observe(CLEAR, 10)
    c.observe(CLEAR, 10.3)
    assert c.command(10.3) == (0, 0)
    assert c.command(10.6) == (0.3, 0.3)


def test_new_object_resets_resume_delay():
    c = CircleControl()
    c.observe([(0.8, 0, 0)], 0)
    c.observe(CLEAR, 0.1)
    c.observe([(0.8, 0, 0)], 0.4)
    c.observe(CLEAR, 0.5)
    c.observe(CLEAR, 0.8)
    assert c.command(0.9) == (0, 0)
    assert c.command(1.01) == (0.3, 0.3)


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

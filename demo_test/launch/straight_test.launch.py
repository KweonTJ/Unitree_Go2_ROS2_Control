"""Drive straight with the existing front lidar stop/resume controller."""

from pathlib import Path

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    return LaunchDescription([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                str(Path(__file__).with_name('circle_test.launch.py'))),
            launch_arguments={'yaw': '0.0', 'node_name': 'straight_test'}.items()),
    ])

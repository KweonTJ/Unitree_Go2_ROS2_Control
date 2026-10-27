"""Run the circle demo with the existing Sport bridge."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

from demo_test.control import DEFAULTS


def generate_launch_description():
    args = [DeclareLaunchArgument(k, default_value=str(v)) for k, v in DEFAULTS.items()]
    strings = dict(lidar_topic='/utlidar/cloud', lidar_frame='utlidar_lidar',
                   output_topic='/cmd_vel')
    args += [DeclareLaunchArgument(k, default_value=v) for k, v in strings.items()]
    args += [DeclareLaunchArgument('start_bridge', default_value='true'),
             DeclareLaunchArgument('dry_run', default_value='false')]
    parameters = {k: ParameterValue(LaunchConfiguration(k), value_type=float)
                  for k in DEFAULTS}
    parameters.update({k: ParameterValue(LaunchConfiguration(k), value_type=str)
                       for k in strings})
    return LaunchDescription(args + [
        Node(package='unitree_go2_teleop', executable='cmd_vel_to_sport',
             condition=IfCondition(LaunchConfiguration('start_bridge')),
             output='screen', parameters=[{
                 'input_topic': LaunchConfiguration('output_topic'),
                 'command_timeout': 0.5,
                 'dry_run': ParameterValue(LaunchConfiguration('dry_run'), value_type=bool),
             }]),
        Node(package='demo_test', executable='circle_test',
             output='screen', parameters=[parameters]),
    ])

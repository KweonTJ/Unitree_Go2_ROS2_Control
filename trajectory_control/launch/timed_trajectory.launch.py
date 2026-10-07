from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():

    vx = LaunchConfiguration('vx')          # 전후진 선속도
    vy = LaunchConfiguration('vy')        # 좌우 횡방향 속도
    yaw = LaunchConfiguration('yaw')        # 회전 속도
    duration = LaunchConfiguration('duration')  # 주행 시간
    publish_rate = LaunchConfiguration('publish_rate')  # 명령 발행 주기

    bridge_node = Node(
        package='unitree_go2_teleop',
        executable='cmd_vel_to_sport',
        name='go2_keyboard_bridge',
        output='screen',
        parameters=[
            {
                'input_topic': '/cmd_vel',
            }
        ]
    )

    trajectory_node = Node(
        package='trajectory_control',
        executable='timed_trajectory',
        name='timed_trajectory',
        output='screen',
        parameters=[
            {
                'output_topic': '/cmd_vel',
                'vx': vx,
                'vy': vy,
                'yaw': yaw,
                'duration': duration,
                'publish_rate': publish_rate,
            }
        ]
    )

    # bridge가 먼저 실행될 시간을 확보한 뒤 trajectory 시작
    delayed_trajectory = TimerAction(
        period=1.0,
        actions=[
            trajectory_node
        ]
    )

    return LaunchDescription([

        DeclareLaunchArgument(
            'vx', 
            default_value='0.0',
            description='Forward velocity [m/s]'
        ),

        DeclareLaunchArgument(
            'vy',
            default_value='0.0',
            description='Lateral velocity [m/s]'
        ),

        DeclareLaunchArgument(
            'yaw',
            default_value='0.0',
            description='Yaw velocity [rad/s]'
        ),

        DeclareLaunchArgument(
            'duration',
            default_value='5.0',
            description='Trajectory duration [s]'
        ),

        DeclareLaunchArgument(
            'publish_rate',
            default_value='50.0',
            description='Command publish rate [Hz]'
        ),

        bridge_node,
        delayed_trajectory,
    ])
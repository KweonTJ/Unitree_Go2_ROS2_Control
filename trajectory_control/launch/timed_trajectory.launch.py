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
    heading_control = LaunchConfiguration('heading_control')  # heading control 활성화 여부
    kp_yaw = LaunchConfiguration('kp_yaw')    # heading control proportional gain
    ki_yaw = LaunchConfiguration('ki_yaw')    # heading control integral gain
    kd_yaw = LaunchConfiguration('kd_yaw')    # heading control derivative gain 
    max_yaw_correction = LaunchConfiguration('max_yaw_correction')  # maximum yaw correction
    # maximum yaw correction
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
                'heading_control': heading_control,
                'kp_yaw': kp_yaw,
                'ki_yaw': ki_yaw,
                'kd_yaw': kd_yaw,
                'max_yaw_correction': max_yaw_correction,
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

        DeclareLaunchArgument(
            'heading_control',
            default_value='true',
            description='Enable heading control'
        ),

        DeclareLaunchArgument(
            'kp_yaw',
            default_value='1.0',
            description='Heading proportional gain'
        ),

        DeclareLaunchArgument(
            'ki_yaw',
            default_value='0.0',
            description='Heading integral gain'
        ),

        DeclareLaunchArgument(
            'kd_yaw',
            default_value='0.05',
            description='Heading derivative gain'
        ),

        DeclareLaunchArgument(
            'max_yaw_correction',
            default_value='0.15',
            description='Maximum yaw correction [rad/s]'
        ),

        bridge_node,
        delayed_trajectory,
    ])
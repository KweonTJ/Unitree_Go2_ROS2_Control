from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():

    # /cmd_vel -> Unitree Sport API
    bridge_node = Node(
        package='unitree_go2_teleop',
        executable='cmd_vel_to_sport',
        name='go2_keyboard_bridge',
        output='screen',
        parameters=[
            {
                'input_topic': '/cmd_vel',
                'request_topic': '/api/sport/request',
                'publish_rate': 50.0,
                'command_timeout': 1.0,
                'dry_run': False,
            }
        ]
    )

    # 키보드 입력 노드
    # 키 입력을 받을 수 있도록 새 터미널에서 실행
    keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        prefix='gnome-terminal --',
        output='screen',
        remappings=[
            ('cmd_vel', '/cmd_vel'),
        ]
    )

    return LaunchDescription([
        bridge_node,
        keyboard_node,
    ])

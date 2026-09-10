from setuptools import find_packages, setup

setup(
    name='unitree_go2_teleop',
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/unitree_go2_teleop']),
        ('share/unitree_go2_teleop', ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='a',
    maintainer_email='a@example.com',
    description='Go2 forward/reverse and yaw teleoperation bridge',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={'console_scripts': [
        'cmd_vel_to_sport = unitree_go2_teleop.bridge:main',
    ]},
)

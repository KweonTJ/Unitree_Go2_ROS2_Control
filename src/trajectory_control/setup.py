from setuptools import find_packages, setup

package_name = 'trajectory_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='a',
    maintainer_email='kweontj0701@naver.com',
    description='Timed velocity trajectory controller for Unitree Go2',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'timed_trajectory = trajectory_control.timed_trajectory:main',
        ],
    },
)

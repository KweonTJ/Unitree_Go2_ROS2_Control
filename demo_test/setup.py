from glob import glob
from setuptools import setup

setup(
    name='demo_test', version='0.1.0', packages=['demo_test'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/demo_test']),
        ('share/demo_test', ['package.xml']),
        ('share/demo_test/launch', glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'], zip_safe=True,
    maintainer='a', maintainer_email='kweontj0701@naver.com',
    description='Circle and straight driving with front lidar stop and resume',
    license='Apache-2.0',
    entry_points={'console_scripts': ['circle_test = demo_test.node:main']},
)

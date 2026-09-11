# Unitree Go2 Ros2 Control Workspace
---
- Unitree Go2를 ROS2 환경에서 제어하기 위해 구현한 ROS2 기반 제어 브리지 패키지
- ROS2의 표준 이동 명령인 `geometry_msgs/Twist`를 입력받아 Unitree Go2의 Sport API 제어 명령으로 변환하여 `teleop_twist_keyboard`와 같은 일반적인 ROS2 입력 장치를 Go2의 실제 주행 제어와 연결
- ROS2 제어 인터페이스와 Unitree Go2 Control API 사이를 연결하는 ROS2 Control Bridge 제공

### 로봇 내부 환경
- Ubuntu 20.04
- ROS2 Foxy
- 공식 unitree_ros2 패키지
- 패키지 위치는 공식 Unitree의 같은 `cyclonedds_ws/src`에 배치한다. 별도 텔레옵 workspace는 필요하지 않다.

## 패키지 구성
---
```
unitree_go2_teleop_ws/
├── src/
│   ├── unitree_go2_teleop/     # 속도 변환·입력 watchdog
│   └── teleop_twist_keyboard/ # 표준 키보드 2.3.2
├── docs/
└── README
```
## Network Interface
---
``` 
~/unitree_ros2/setup.sh

#!/bin/bash

echo "Setup unitree ros2 environment"

source /opt/ros/foxy/setup.bash
source $HOME/unitree_ros2/cyclonedds_ws/install/setup.bash

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_DOMAIN_ID=0

export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces>
<NetworkInterface name="eth0" priority="default" multicast="default" />
</Interfaces></General></Domain></CycloneDDS>'
```
- Go2 내부 네트워크 주소와 DDS 내부 주소가 불일치 문제를 인터페이스 이름 기반으로 묶어서 통신
## 패키지 빌드
---
-  `unitree_ros2/cyclonedds_ws/src/`에 있는 **`unitree_go2_teleop`, `teleop_twist_keyboard` 두 폴더**를 로봇의 `~/unitree_ros2/cyclonedds_ws/src/`에 넣고 로봇에서 빌드한다.

```
cd ~/unitree_ros2/cyclonedds_ws
source ~/unitree_ros2/setup.sh

colcon build --symlink-install \
  --packages-select teleop_twist_keyboard unitree_go2_teleop

source install/setup.bash
```
## 로봇 주행
---
### 터미널 1 : 명령 변환 노드

```
ros2 run unitree_go2_teleop cmd_vel_to_sport \
  --ros-args \
  -p dry_run:=false \
  -p max_linear:=0.3
```
- 이동 속도 : max_linear를 키워서 실행시킨다.
### 터미널 2 : 키보드 텔레옵

```
ros2 run teleop_twist_keyboard teleop_twist_keyboard \
  --ros-args \
  -r cmd_vel:=/go2_teleop/cmd_vel
```
- vy 부분 제어는 구현되어 있지 않아, 옆으로 걷는 주행 불가 (기본 주행 및 회전과는 무관)
### 주행 결과
- 전진, 후진 시에 사용자가 의도한 곳으로 정확하게 이동하고, 몸체의 쏠림 문제 없음
- 회전시에 몸체가 먼저 회전하고 그 이후 다리가 회전하지만, 주행 테스트에서는 문제 없음

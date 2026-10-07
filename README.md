# Unitree Go2 Ros2 Control Workspace
  

- Unitree Go2를 ROS2 환경에서 제어하기 위해 구현한 ROS2 기반 제어 브리지 패키지
- ROS2의 표준 이동 명령인 `geometry_msgs/Twist`를 입력받아 Unitree Go2의 Sport API 제어 명령으로 변환하여 일반적인 ROS2 입력을 Go2의 실제 주행 제어와 연결
- teleop_twist_keyboard를 이용한 키보드 주행과 시간 기반 Trajectory 주행 지원
- ROS2 제어 인터페이스와 Unitree Go2 Control API 사이를 연결하는 ROS2 Control Bridge 제공
- 추후 ROS2 기반 Path Follower 및 자율주행 제어로 확장하기 위한 기본 주행 구조 제공

  

### 로봇 내부 환경

- Ubuntu 20.04
- ROS2 Foxy
- 공식 unitree_ros2 패키지
- 패키지 위치는 공식 Unitree의 같은 `cyclonedds_ws/src`에 배치. 

  

## 패키지 구성

```

cyclonedds_ws/
├── src/
│ ├── unitree/
│ ├── cyclonedds/
│ ├── rmw_cyclonedds/
│ │
│ ├── unitree_go2_teleop/
│ │ ├── launch/
│ │ │ └── keyboard_teleop.launch.py
│ │ │
│ │ └── unitree_go2_teleop/
│ │ ├── bridge.py
│ │ └── control.py
│ │
│ ├── teleop_twist_keyboard/
│ │
│ └── trajectory_control/
│ ├── launch/
│ │ └── timed_trajectory.launch.py
│ │
│ └── trajectory_control/
│ └── timed_trajectory.py
│
├── build/
├── install/
└── log/

```

### 1. unitree_go2_teleop
- ROS2 /cmd_vel topic을 받아 Unitree Go2의 Sport API 명령 변환 패키지
#### 입력
```text
geometry_msgs/Twist
/cmd_vel
```
#### 출력
```text
unitree_api/Request
/api/sport/request
```
#### 기본 동작 구조
```text
/cmd_vel
    ↓
cmd_vel_to_sport
    ↓
Unitree Sport API
    ↓
Go2
```
#### 주요 기능
- `vx` 전진 / 후진 명령
- `vy` 좌우 이동 명령
- `yaw` 회전 명령
- 최대 속도 제한
- command timeout 처리
- 정지 명령 처리
- Unitree Sport API `Move` / `StopMove` 요청 생성
### 2. trajectory_control
- 사용자가 지정한 속도, 시간에 따라 Go2를 일정 시간 주행시키는 패키지
- 추후 ROS2 기반 Path 주행 확장을 위한 기본 패키지
#### 입력
```text
vx
vy
yaw
duration
publish_rate
```
#### 변수
```text
vx           전진 / 후진 속도 [m/s]
vy           좌우 이동 속도 [m/s]
yaw          회전 속도 [rad/s]
duration     해당 명령 유지 시간 [s]
publish_rate /cmd_vel 발행 주기 [Hz]
```
#### 주행 구조
```text
timed_trajectory
    ↓
/cmd_vel
    ↓
cmd_vel_to_sport
    ↓
/api/sport/request
    ↓
Go2
```

## 패키지 빌드

-  `unitree_ros2/cyclonedds_ws/src/`에 있는 **`unitree_go2_teleop`, `teleop_twist_keyboard`, `trajectory_control` 세 폴더**를 로봇의 `~/unitree_ros2/cyclonedds_ws/src/`에 넣고 로봇에서 빌드한다.

```bash
cd ~/unitree_ros2/cyclonedds_ws

source ~/unitree_ros2/setup.sh
```

```bash
colcon build --symlink-install \
    --packages-select \
    teleop_twist_keyboard \
    unitree_go2_teleop \
    trajectory_control
    
source install/setup.bash
```


## 로봇 제어

### Control structure

```
                   ROS2 Control Input
                          │
            ┌─────────────┴─────────────┐
            │                           │
            ▼                           ▼
teleop_twist_keyboard            trajectory_control
            │                           │
            └─────────────┬─────────────┘
                          │
                      /cmd_vel
                          │
                          ▼
                  unitree_go2_teleop
                  cmd_vel_to_sport
                          │
                          ▼
                 /api/sport/request
                          │
                          ▼
                    Unitree Go2
```

### Keyboard teleop Control

```bash
ros2 launch unitree_go2_teleop keyboard_teleop.launch.py
```
- 이동 속도 : max_linear를 키워서 실행시킨다.


### Trajectory Control

```bash
ros2 launch trajectory_control timed_trajectory.launch.py \
    vx:=0.3 \
    duration:=5.0
```

- 이동 속도는 최소 0.3이어야 전진함
### 주행 결과

#### 키보드 텔레옵

- 전진, 후진 시에 사용자가 의도한 방향으로 정상적으로 이동
- 기존에 발생하던 전진 시 몸체 쏠림 문제 없음
- 전진 및 후진 연속 주행 가능
- ROS2 `/cmd_vel` 명령을 이용한 실제 Go2 제어 가능
- 회전시에 몸체가 먼저 회전하고 그 이후 다리가 회전하는 현상이 있지만 현재 주행 테스트에서는 문제 없이 동작

#### Trajectory Control

- 사용자가 입력한 `vx`, `vy`, `yaw` 값에 따라 `/cmd_vel` 명령 생성
- 지정한 `duration` 동안 일정한 주행 명령 유지
- 설정 시간이 종료되면 자동 정지
- `cmd_vel_to_sport` Bridge가 launch에서 함께 실행되기 때문에 별도의 Bridge 실행 과정이 필요하지 않음
- 전진, 후진, 횡이동, 회전 및 전진 + 회전 명령 사용 가능
- 추후 시간 기반 명령을 여러 개 연결하여 연속 Trajectory 주행으로 확장 가능

---

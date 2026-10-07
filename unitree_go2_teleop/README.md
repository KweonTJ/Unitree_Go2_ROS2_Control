# Go2 기본 주행·회전 키보드 텔레옵

작성일: 2026-09-10 (Asia/Seoul). 목표 환경: 로봇 내부 Ubuntu 20.04 / ROS 2 Foxy / 공식 `unitree_ros2`.

`teleop_twist_keyboard → /go2_teleop/cmd_vel → cmd_vel_to_sport → /api/sport/request` 구성이다. 키보드 노드와 변환 노드를 모두 로봇 내부에서 실행하고 PC는 Wi-Fi SSH 터미널로 입력한다.

두 패키지 모두 공식 Unitree의 **같은 `cyclonedds_ws/src`**에 배치한다. 별도 텔레옵 workspace는 필요하지 않다.

```text
unitree_ros2/cyclonedds_ws/
├── src/
│   ├── cyclonedds/             # 기존 Foxy DDS 소스
│   ├── rmw_cyclonedds/         # 기존 Foxy RMW 소스
│   ├── unitree/
│   │   ├── unitree_api/
│   │   ├── unitree_go/
│   │   └── unitree_hg/
│   ├── teleop_twist_keyboard/  # 표준 키보드 2.3.2
│   └── unitree_go2_teleop/     # 이 변환 패키지
└── install/setup.bash
```

## 구현 범위와 키

| 키 | 동작 | 기본 변환 출력 |
|---|---|---|
| `i` | 전진 | vx 최대 +0.2 m/s |
| `,` | 후진 | vx 최대 -0.2 m/s |
| `j` / `l` | 제자리 좌 / 우 회전 | yaw 최대 +0.4 / -0.4 rad/s |
| `u` / `o` | 전진하며 좌 / 우 회전 | vx + yaw 동시 명령 |
| `m` / `.` | 후진하며 양 방향 회전 | vx 음수 + yaw 양수 / 음수 |
| `k` 또는 Space | 정지 | StopMove 1003 |
| Ctrl+C | 키보드 종료 | 키보드의 0 입력 또는 입력 타임아웃으로 정지 요청 |

곡선 주행은 일정 vx와 yaw rate를 함께 보내는 기능이다. 실제 이동 거리나 회전 각도까지 맞추는 폐루프 제어는 포함하지 않는다. 좌우 평행이동 및 나머지 축의 비영 입력은 거부하고 정지한다.

키를 반복 입력하거나 누르고 있어야 주행이 이어진다. 일반 터미널은 키를 놓은 사건을 전달하지 않으므로, **키를 놓는 즉시가 아니라 마지막으로 수신한 입력 이후 기본 0.5초가 지나면** 정지를 요청한다. 키 반복의 초기 지연이 0.5초보다 길면 처음 누를 때 잠시 멈출 수 있다. 즉시 정지는 `k`를 사용한다. ROS 1의 `repeat_rate`/`key_timeout` 옵션을 Foxy 키보드에 그대로 적용하지 않는다.

## 로봇 내부 설치

이 PC의 `unitree_ros2/cyclonedds_ws/src/`에 있는 **`unitree_go2_teleop`, `teleop_twist_keyboard` 두 폴더**를 로봇의 `~/unitree_ros2/cyclonedds_ws/src/`에 넣고 로봇에서 빌드한다. 기존 `unitree`·DDS 폴더는 유지한다. PC의 Humble `build/`, `install/`는 로봇에 복사하지 않는다. 아래 공식 패키지 경로는 `~/unitree_ros2`라고 가정한다.

```bash
source /opt/ros/foxy/setup.bash
source ~/unitree_ros2/cyclonedds_ws/install/setup.bash

cd ~/unitree_ros2/cyclonedds_ws
colcon build --symlink-install --packages-select teleop_twist_keyboard unitree_go2_teleop
source install/setup.bash
ros2 pkg executables unitree_go2_teleop
ros2 pkg executables teleop_twist_keyboard
```

공식 `unitree_api`와 Foxy용 CycloneDDS 환경이 먼저 빌드되어 있어야 한다. 아직 공식 메시지 패키지를 빌드하지 않았다면 공식 Foxy DDS 설치 절차를 마친 후 같은 workspace에서 `colcon build --symlink-install --packages-select unitree_api unitree_go unitree_hg teleop_twist_keyboard unitree_go2_teleop`로 메시지와 텔레옵을 함께 빌드한다. Python 실행환경은 ROS 설치와 맞는 시스템 Python을 사용한다. 키보드 소스를 포함했으므로 `ros-foxy-teleop-twist-keyboard`의 별도 apt 설치는 필요하지 않다.

## 두 SSH 터미널의 공통 환경

SSH 명령에서 프로그램을 바로 시작한다면 `ssh -t 사용자@로봇_WiFi_IP ...`로 TTY를 할당한다. 일반 대화형 SSH 터미널에서는 그대로 키를 입력하면 된다.

```bash
source /opt/ros/foxy/setup.bash
source ~/unitree_ros2/cyclonedds_ws/install/setup.bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

ip -br addr
ip route
printenv ROS_DISTRO ROS_DOMAIN_ID ROS_LOCALHOST_ONLY CYCLONEDDS_URI
```

`CYCLONEDDS_URI`는 로봇 **내부 운동 제어기와 통신하는 인터페이스**를 선택한다. Wi-Fi SSH 인터페이스와 같다고 가정하지 않는다. 예를 들어 실제로 확인된 내부 인터페이스가 `eth0`일 때만 다음을 사용한다.

```bash
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="eth0" priority="default" multicast="default" /></Interfaces></General></Domain></CycloneDDS>'
```

두 터미널은 운동 제어기와 맞는 동일한 DDS domain을 사용한다. 별도 내부 제어기와 통신한다면 `ROS_LOCALHOST_ONLY=1`이나 인터페이스 `lo`로 제한하지 않는다. 이미 상태 데이터가 수신되는 로봇 설정을 우선한다. PC에서 발견된 `~/unitree_ros2/setup.sh`는 Humble을 source하도록 기존 수정되어 있으므로 이를 Foxy 로봇에 그대로 복사하지 않는다.

```bash
ros2 topic list
# 목록에 나타난 상태 토픽을 선택해서 실제 수신 확인 후 Ctrl+C
ros2 topic echo /lf/sportmodestate
# /sportmodestate만 있다면 해당 이름 사용
```

## 먼저 명령 변환 확인

터미널 A:

```bash
ros2 run unitree_go2_teleop cmd_vel_to_sport
```

기본 `dry_run=true`에서는 Unitree 요청 publisher를 만들지 않고 변환 내용을 로그에 출력한다.

터미널 B:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -r cmd_vel:=/go2_teleop/cmd_vel
```

키보드 `i`, `,`, `j`, `l`, `u`, `o`, `k`에 따라 A의 `api_id=1008` 속도 JSON과 `api_id=1003` 정지 로그를 확인한다. 키 입력을 멈췄을 때 정지 로그도 확인한다. 키보드 기본 속도가 더 커도 변환 노드에서 제한한다.

## 실제 로봇 주행

정상 Sport Mode로 서 있는 로봇에서 다른 이동 명령 발행기를 종료하고 사용한다. 이 패키지는 기립이나 모드 전환을 자동 실행하지 않는다. 변환 노드를 종료한 뒤 터미널 A에서 다음으로 다시 실행한다.

```bash
ros2 run unitree_go2_teleop cmd_vel_to_sport --ros-args -p dry_run:=false
```

터미널 B의 키보드는 같은 명령을 사용한다. 처음에는 `i → k`, `, → k`, `j → k`, `l → k`, `u → k`, `o → k` 순서로 확인한다. 실물 비상정지 수단을 준비한다. `StopMove`는 소프트웨어 정지 요청이며 수신·물리적 정지를 보장하는 비상정지 장치는 아니다.

기본 동작:

- 전후 속도 제한 0.2 m/s, yaw rate 제한 0.4 rad/s.
- 최근 입력을 20 Hz로 발행. 입력 중단 후 기본 0.5초 + 타이머/실행 지연 이내에 정지 요청을 시작한다.
- 정지는 기본 0.5초 동안 재전송한 뒤 발행을 멈춘다. 시작 직후에는 이동·정지 요청을 발행하지 않는다.
- NaN/Inf, 지원하지 않는 축 입력은 정지 요청으로 처리한다.
- 정상 종료 및 SIGINT/SIGTERM/SIGHUP 처리 시 활성 명령이 있으면 정지를 최대 5회 시도한다.
- 설정은 시작 시 고정하며 변경 시 노드를 재시작한다. 예: `-p max_linear:=0.1 -p max_yaw:=0.2`.

SSH 입력이 끊겨도 변환 노드가 계속 실행되고 DDS가 정상이어야 watchdog 정지가 전달된다. 프로세스 강제 종료, 전원 차단, DDS 단절은 이 노드만으로 정지를 보장할 수 없다. Twist에는 입력 시각이 없으므로 SSH 지연으로 늦게 도착한 키를 생성 시점 기준으로 판별할 수 없다.

## 검증과 근거

검증 환경과 결과는 [최초 구현 기록](docs/1-basic-driving-and-turning.md)과 [워크스페이스 통합 기록](docs/2-cyclonedds-workspace-integration.md)에 기록한다.

- [공식 Unitree ROS 2 설치·DDS 설정](https://github.com/unitreerobotics/unitree_ros2)
- [공식 Move / StopMove 구현](https://github.com/unitreerobotics/unitree_ros2/blob/master/example/src/src/common/ros2_sport_client.cpp)
- [공식 API 번호](https://github.com/unitreerobotics/unitree_ros2/blob/master/example/src/include/common/ros2_sport_client.h)
- [키보드 구버전 소스](https://github.com/ros2/teleop_twist_keyboard/blob/2.3.2/teleop_twist_keyboard.py)

# 원형·직진 주행 테스트

위치·오도메트리·IMU 없이 일정한 `vx`, `yaw`를 `/cmd_vel`로 전송한다.
런치 실행 후 첫 타이머부터 기본 속도로 주행하며, 라이다의 첫 입력이나
시작 전 clear 판정을 기다리지 않는다. 라이다는 주행 중 장애물 감시에 사용한다.
전방 영역에서 임계 거리 이내 포인트가 하나라도 검출되면 전진과 회전을 모두
0으로 전송한다. 기존 브리지가 이를 Sport `StopMove`로 변환한다.
회피·후진·앉기 동작은 하지 않는다. 물체가 사라지고 연속 0.5초 동안
유효한 clear 입력이 유지되면 설정한 주행을 재개한다.
`vx`, `yaw`는 시작 시 지정할 수 있고, 실행 중에도 ROS 파라미터로 변경할 수 있다.

## 빌드와 실행

로봇의 기존 ROS 2 워크스페이스 `src`에 `demo_test`와
`unitree_go2_teleop`을 배치하고 기존 Unitree ROS 환경을 source한다.

```bash
colcon build --symlink-install --packages-select unitree_go2_teleop demo_test
source install/setup.bash
ros2 launch demo_test circle_test.launch.py
```

기본값은 `vx=0.3 m/s`, `yaw=0.3 rad/s`다. 명령상 반지름은 1 m이며
실제 궤적을 보정하지 않는다. 음수 yaw는 반대 방향 회전이다.
데모의 전진 속도 상한은 0.5 m/s이며, 함께 실행하는 브리지의 `max_linear`도
0.5로 설정한다. 회전 속도 상한은 절댓값 0.4 rad/s다.

```bash
ros2 launch demo_test circle_test.launch.py \
  lidar_topic:=/utlidar/cloud lidar_frame:=utlidar_lidar \
  vx:=0.3 yaw:=0.3 stop_distance:=1.0
```

## 직진 및 장애물 정지 테스트

```bash
ros2 launch demo_test straight_test.launch.py
# 시작 속도를 지정할 때
ros2 launch demo_test straight_test.launch.py vx:=0.5 stop_distance:=1.0
```

`straight_test.launch.py`는 기존 런치를 재사용하면서 `yaw=0.0`, 노드 이름을
`straight_test`로 설정한다. 기본 전진 속도는 0.3 m/s이며 0.5 m/s까지 지정할 수 있다.
런치 실행 후 먼저 직진하고, 전방 물체 감지 시 모든 속도를 0으로 전송한다.
물체가 사라지고 clear 입력이 0.5초간 유지되면 설정한 속도로 다시 직진한다.
라이다 토픽·거리·높이·timeout·브리지 설정은 원형 주행과 같다.
각속도 명령은 0이며 위치·IMU 기반 방향 보정은 하지 않는다.
원형 런치와 직진 런치는 하나씩 실행한다.

실행 중 직진 속도 변경 및 목표값 조회:

```bash
ros2 param set /straight_test vx 0.5
ros2 param get /straight_test vx
```

직진 런치는 시작 각속도를 0으로 고정한다. 실행 중에도 직진을 유지하려면
`yaw`를 0.0으로 유지한다. `dry_run:=true output_topic:=/demo_test/cmd_vel`도 사용할 수 있다.

## 주행 중 속도·각속도 변경

원형 런치를 실행한 채, 동일한 ROS 환경을 source한 다른 터미널에서 변경한다.
노드를 재시작하지 않아도 다음 제어 주기(기본 20 Hz)에 새 목표값이 반영된다.

```bash
# 전진 속도 [m/s]
ros2 param set /circle_test vx 0.5
# 각속도 [rad/s], 음수는 반대 방향 회전
ros2 param set /circle_test yaw -0.2

# 현재 목표값 확인
ros2 param get /circle_test vx
ros2 param get /circle_test yaw
```

허용 범위는 `0.0 <= vx <= 0.5`, `-0.4 <= yaw <= 0.4`이며,
`0` 대신 `0.0`처럼 실수로 입력한다. 범위 초과·NaN·Inf·잘못된 타입은 거부하고
이전 목표값을 유지한다. 각 `param set` 명령은 해당 항목을 개별 변경한다.
`yaw=0.0`이면 직진하고, `vx=0.0`이면 전진 없이 회전하며, 둘 다 0이면 정지한다.
장애물로 정지해 있을 때 변경해도 정지는 유지하며, 물체가 사라지면 새 목표값으로
재개한다. `get`은 정지 중 실제 출력 0이 아니라 설정된 목표값을 보여준다.
변경값은 현재 실행에 적용되며, 재실행할 때는 launch의 `vx:=`, `yaw:=` 값이 적용된다.
나머지 파라미터는 시작 시에만 지정한다.
0.5 m/s로 시작하려면 `ros2 launch demo_test circle_test.launch.py vx:=0.5`를 사용한다.
`start_bridge:=false`로 별도 브리지를 사용하는 경우 해당 브리지도
`max_linear:=0.5` 이상으로 실행해야 0.3 m/s로 제한되지 않는다.

## 라이다 입력 계약

현재 저장소에 기본 물체 인지 토픽 정의가 없어 `/utlidar/cloud`의
`sensor_msgs/msg/PointCloud2`를 기본 입력으로 가정했다. 실제 토픽과 타입은
아직 로봇에서 확인하지 않았다. 기존 물체 인지 출력이 Bool·거리 메시지라면
해당 메시지용 입력 어댑터가 추가로 필요하다.

```bash
ros2 topic list -t
ros2 topic info /utlidar/cloud -v
ros2 topic echo /utlidar/cloud --once --field header
```

포인트는 **라이다 원점, x 전방·y 좌측·z 위쪽인 로봇에 고정된 좌표계**여야 한다.
`lidar_frame`은 해당 frame_id와 정확히 일치시킨다. 좌표 변환은 하지 않으며
world/odom 좌표의 cloud는 사용할 수 없다. 센서 장착 방향도 확인해야 한다.
거리 임계값은 로봇 외곽이 아닌 라이다 원점 기준 수평 거리다.

| 인자 | 기본값 | 의미 |
|---|---:|---|
| vx | 0.3 | 전진 목표 속도 [m/s], 실행 중 변경 가능 |
| yaw | 원형 0.3 / 직진 0.0 | 목표 각속도 [rad/s], 실행 중 변경 가능 |
| stop_distance | 1.0 | 정지 거리 [m], 경계 포함 |
| front_angle_deg | 60.0 | 전방 부채꼴 전체 각도 [deg] |
| min_height / max_height | -0.2 / 0.5 | 라이다 원점 기준 z 범위 [m] |
| lidar_timeout | 0.5 | 첫 유효 입력 이후 수신 중단 시 정지 [s] |
| clear_duration | 0.5 | 정지 후 clear 지속 시 재개 [s], 시작 대기에는 사용하지 않음 |
| publish_rate | 20.0 | 명령 전송 주기 [Hz] |
| output_topic | /cmd_vel | 기존 브리지 입력 |
| start_bridge | true | 기존 브리지 함께 실행 |
| dry_run | false | true면 브리지 Sport 요청 발행 생략 |

높이 범위는 바닥·로봇 자체 포인트가 포함되지 않도록 실제 cloud에서 조정한다.
첫 라이다 메시지가 오기 전에는 주행을 유지한다. 빈 cloud·유한 좌표 없음·
frame 불일치·디코딩 실패 또는 첫 유효 수신 이후 수신 중단에서는 정지한다.
잘못된 입력으로 정지했다면 유효한 clear 입력을 확인한 뒤 재개한다.
따라서 비어 있는 감지 결과만 발행하는 희소 cloud는 이 입력 계약에
맞지 않는다. 센서 QoS는 best effort다. timeout은 수신 시각 기준이며
센서 헤더의 지연을 검사하지 않는다.

## 검증

```bash
PYTHONPATH=demo_test:unitree_go2_teleop:$PYTHONPATH python3 -m pytest demo_test/test -q
```

실물 없이 Sport 요청을 막고 명령을 확인하려면 다른 주행 노드와 브리지를
종료한 상태에서 다음과 같이 전용 토픽으로 실행한다.

```bash
ros2 launch demo_test circle_test.launch.py dry_run:=true output_topic:=/demo_test/cmd_vel
ros2 topic echo /demo_test/cmd_vel
```

라이다 입력 없이 원형/직진 명령 시작 → 전방 물체 → 모든 속도 0 유지 → 물체 제거
→ 재개, 그리고 cloud 중단 → 정지를 확인한다. `dry_run`은 함께 실행한
브리지에만 적용된다. 실제 실행 중에도 다른 `/cmd_vel` 발행자를 함께 실행하지 않는다.
Ctrl+C에서는 0 명령을 반복 전송하고, 브리지도 종료 전 정지를 수행한다.

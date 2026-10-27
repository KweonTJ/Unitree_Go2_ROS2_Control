# 원형 주행 테스트

위치·오도메트리·IMU 없이 일정한 `vx`, `yaw`를 `/cmd_vel`로 전송한다.
런치 실행 후 첫 타이머부터 기본 속도로 주행하며, 라이다의 첫 입력이나
시작 전 clear 판정을 기다리지 않는다. 라이다는 주행 중 장애물 감시에 사용한다.
전방 영역에서 임계 거리 이내 포인트가 하나라도 검출되면 전진과 회전을 모두
0으로 전송한다. 기존 브리지가 이를 Sport `StopMove`로 변환한다.
회피·후진·앉기 동작은 하지 않는다. 물체가 사라지고 연속 0.5초 동안
유효한 clear 입력이 유지되면 동일한 원형 주행을 재개한다.

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
기존 브리지와 같은 속도 상한(전진 0.3 m/s, 회전 절댓값 0.4 rad/s)을 적용한다.

```bash
ros2 launch demo_test circle_test.launch.py \
  lidar_topic:=/utlidar/cloud lidar_frame:=utlidar_lidar \
  vx:=0.3 yaw:=0.3 stop_distance:=1.0
```

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
PYTHONPATH=demo_test python3 -m pytest demo_test/test -q
```

실물 없이 Sport 요청을 막고 명령을 확인하려면 다른 주행 노드와 브리지를
종료한 상태에서 다음과 같이 전용 토픽으로 실행한다.

```bash
ros2 launch demo_test circle_test.launch.py dry_run:=true output_topic:=/demo_test/cmd_vel
ros2 topic echo /demo_test/cmd_vel
```

라이다 입력 없이 원형 명령 시작 → 전방 물체 → 모든 속도 0 유지 → 물체 제거
→ 재개, 그리고 cloud 중단 → 정지를 확인한다. `dry_run`은 함께 실행한
브리지에만 적용된다. 실제 실행 중에도 다른 `/cmd_vel` 발행자를 함께 실행하지 않는다.
Ctrl+C에서는 0 명령을 반복 전송하고, 브리지도 종료 전 정지를 수행한다.

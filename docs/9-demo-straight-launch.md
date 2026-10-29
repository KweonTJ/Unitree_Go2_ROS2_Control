# 9. 직진 및 장애물 정지 데모 런치 추가

- 수정일: 2026-10-27 (Asia/Seoul)
- 목적: 기존 원형 주행 런치와 별도로 직진 → 전방 물체 감지 시 정지 →
  물체 제거 후 재개하는 런치를 추가한다.
- 이전 변경 기록: [8. 데모 전진 속도 상한 0.5 m/s](8-demo-speed-limit-05.md).
- [`straight_test.launch.py`](../demo_test/launch/straight_test.launch.py)의
  `generate_launch_description`: 원형 런치를 포함하고 시작 각속도는 0.0,
  노드 이름은 `straight_test`로 지정한다. 속도·라이다·브리지 인자는 기존 구성을 사용한다.
- [`circle_test.launch.py`](../demo_test/launch/circle_test.launch.py)의
  `generate_launch_description`: 노드 이름을 지정하는 `node_name` 인자를 추가한다.
  원형 런치 기본 이름은 기존 `circle_test`를 유지한다.
- [`node.py`](../demo_test/demo_test/node.py)의 시작 로그와 패키지 설명을
  원형·직진 공통 동작에 맞게 수정한다. 정지·재개 로직은 기존 코드를 재사용한다.
- 기본값: `vx=0.3 m/s`, `yaw=0.0 rad/s`. 시작 속도와 실행 중 `vx`는
  0.5 m/s까지 허용한다. 위치·IMU 방향 보정은 추가하지 않는다.
- 실행: `ros2 launch demo_test straight_test.launch.py`.
  실행 중 속도 변경: `ros2 param set /straight_test vx 0.5`.
- [`test_launch.py`](../demo_test/test/test_launch.py): 두 런치의 포함 구조와 인자를
  해석해 원형·직진 기본 각속도, 0.5 m/s 전달, StopMove·재개를 확인한다.
- [`test_node.py`](../demo_test/test/test_node.py): 실제 ROS 메시지 콜백으로
  직진·물체 감지 정지·정지 중 속도 변경·새 속도로 직진 재개를 확인한다.
- 검증: `PYTHONPATH=demo_test:unitree_go2_teleop:$PYTHONPATH /usr/bin/python3
  -m pytest demo_test/test -q`에서 48개 통과. `git diff --check` 통과.
- 실물 주행: 미실행.

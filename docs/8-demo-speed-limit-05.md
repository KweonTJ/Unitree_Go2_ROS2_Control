# 8. 데모 전진 속도 상한 0.5 m/s

- 수정일: 2026-10-27 (Asia/Seoul)
- 목적: 사용자가 데모 전진 속도를 0.5 m/s까지 지정할 수 있도록 한다.
- 이전 변경 기록: [7. 데모 실행 중 속도 및 각속도 조정](7-demo-runtime-velocity.md).
- [`control.py`](../demo_test/demo_test/control.py): `MAX_VX=0.5`와
  `validate_velocity`로 시작값·실행 중 변경값의 상한을 0.5 m/s로 설정한다.
- [`circle_test.launch.py`](../demo_test/launch/circle_test.launch.py): 데모와
  함께 실행되는 브리지의 `max_linear`에 같은 상한을 전달하여 0.3 m/s에서
  명령이 잘리는 문제를 방지한다.
- 기본 전진 속도는 0.3 m/s, 기본 각속도는 0.3 rad/s를 유지한다.
  각속도 범위는 -0.4–0.4 rad/s다. 공통 브리지 및 다른 주행 런치는 수정하지 않는다.
- 사용: 시작 시 `vx:=0.5`, 실행 중 `ros2 param set /circle_test vx 0.5`.
  별도 브리지를 실행할 때도 `max_linear:=0.5` 이상으로 설정한다.
- [`test_control.py`](../demo_test/test/test_control.py) 및
  [`test_node.py`](../demo_test/test/test_node.py): 상한값 시작·변경·장애물 정지 후
  재개와 0.51 m/s 거부를 확인한다.
- [`test_launch.py`](../demo_test/test/test_launch.py): 런치의 브리지 설정을
  실제 브리지 제어 로직에 적용해 0.5 m/s Move 및 장애물 StopMove·재개를 검증한다.
  DDS 및 실물 명령은 발행하지 않는다.
- 검증: `PYTHONPATH=demo_test:unitree_go2_teleop:$PYTHONPATH /usr/bin/python3
  -m pytest demo_test/test -q`에서 46개 통과. `git diff --check` 통과.
- 실물 0.5 m/s 주행: 미실행.

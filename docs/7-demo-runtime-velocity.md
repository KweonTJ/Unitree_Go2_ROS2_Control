# 7. 데모 실행 중 속도 및 각속도 조정

- 수정일: 2026-10-27 (Asia/Seoul)
- 목적: 처음 지정한 속도로 주행을 시작하고, 사용자가 필요할 때 노드를
  재시작하지 않고 전진 속도와 각속도를 조정한다.
- 이전 변경 기록: [6. 데모 시작 즉시 원형 주행](6-demo-immediate-driving.md).
- [`control.py`](../demo_test/demo_test/control.py): `validate_velocity`로 시작값과
  변경값을 검사하고, `CircleControl.set_velocity`에서 장애물 정지 상태와
  clear 확인 시각을 유지한 채 목표 속도만 갱신한다.
- [`node.py`](../demo_test/demo_test/node.py): `CircleNode.__init__`에서 `vx`와
  `yaw`만 쓰기 가능한 파라미터로 선언한다. `on_parameters`는 새 값을 검증하며
  주행 상태를 변경하지 않는다. `tick`에서 ROS에 저장된 값을 읽어 반영하므로
  거부된 파라미터 요청이 주행에 영향을 주지 않는다. 주행 출력 로그에는
  적용된 속도와 각속도를 표시한다.
- 허용 범위: `vx` 0.0–0.3 m/s, `yaw` -0.4–0.4 rad/s. 0도 허용해
  직진·제자리 회전·수동 정지를 설정할 수 있다. NaN·Inf·범위 초과·잘못된 타입은
  거부한다. 기본값은 기존 `vx=0.3`, `yaw=0.3`을 유지한다.
- 실행 중 `ros2 param set /circle_test vx 0.2`,
  `ros2 param set /circle_test yaw -0.2`로 개별 변경한다.
  다음 타이머 또는 cloud 콜백에서 반영한다. 장애물 정지는 속도 변경보다 우선하며
  물체가 사라진 뒤 최신 목표값으로 재개한다. 변경값은 실행을 종료하면 저장되지 않는다.
- [`README.md`](../demo_test/README.md): 시작값 지정·실행 중 변경·목표값 조회·
  허용 범위·정지 중 변경 동작을 기록한다.
- 검증: `PYTHONPATH=demo_test:$PYTHONPATH /usr/bin/python3 -m pytest
  demo_test/test -q`에서 41개 통과. `git diff --check` 통과.
- 검증 범위: 상태 로직, 실제 PointCloud2·Twist를 사용한 콜백 테스트와
  ROS 통신을 모킹한 파라미터 선언·등록 확인. 실물 주행 및 원격 파라미터 서비스
  통신은 미실행.

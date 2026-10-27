# 6. 데모 시작 즉시 원형 주행

- 수정일: 2026-10-27 (Asia/Seoul)
- 요구사항: 런치 실행 후 먼저 원형 주행하고, 주행 중 라이다에 전방 물체가
  감지되면 정지하며 물체가 사라지면 재개한다. 시작 전에 라이다를 기다리지 않는다.
- 이전 변경 기록: [5. 원형 주행 및 전방 라이다 정지 데모](5-circle-driving-demo.md).
- 수정 파일·함수:
  - [`control.py`](../demo_test/demo_test/control.py)의 `CircleControl.__init__`,
    `invalidate`, `observe`, `command`: 초기 상태를 주행으로 두고, 첫 입력 전에는
    기본 `vx=0.3 m/s`, `yaw=0.3 rad/s`를 반환한다. 감지·입력 오류·수신 중단 후
    정지 상태를 별도로 유지하며 clear 지속 조건은 정지 후 재개에만 적용한다.
  - [`node.py`](../demo_test/demo_test/node.py)의 `CircleNode.__init__`:
    시작 로그를 라이다 대기에서 주행 시작 및 장애물 감시로 수정한다.
  - [`test_control.py`](../demo_test/test/test_control.py): 첫 입력 없이 주행,
    첫 clear 입력에서 주행 유지, 첫 입력부터 물체 감지 시 정지, 제거 후 재개,
    재감지 시 대기 초기화와 입력 오류 후 정지 유지 검증.
  - [`test_node.py`](../demo_test/test/test_node.py): DDS를 시작하지 않고 실제
    PointCloud2를 생성해 첫 타이머의 Twist와 감지·제거·수신 중단·frame 오류의
    전체 6축 속도를 검증한다. 테스트 입력용 `std_msgs` 의존성을 추가한다.
  - [`README.md`](../demo_test/README.md): 시작 조건과 수신 중단의 적용 시점을 갱신한다.
- 라이다 구독과 주행 명령은 병행한다. 기존 20 Hz 타이머의 첫 호출부터
  주행 명령을 발행한다. 라이다 토픽은 `/utlidar/cloud`를 유지한다.
- 첫 메시지가 끝내 오지 않아도 초기 주행은 유지한다. 유효 수신을 시작한 뒤
  0.5초 이상 끊기면 정지한다. 정지 후에는 유효한 clear 입력이 0.5초간
  유지되어야 재개한다. 빈 cloud를 장애물 제거로 취급하지 않는다.
- 기존 브리지와 `trajectory_control`은 수정하지 않는다.
- 검증 결과: `PYTHONPATH=demo_test:$PYTHONPATH /usr/bin/python3 -m pytest
  demo_test/test -q`에서 23개 통과. `git diff --check` 통과.
- 실물 주행: 미실행.

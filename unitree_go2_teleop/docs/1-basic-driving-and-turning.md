# 1. 기본 주행·회전 변환 노드

- 수정일: 2026-09-10 (Asia/Seoul)
- 목적: 로봇 내부 Foxy에서 키보드 Twist를 공식 Go2 Sport API로 변환.
- 현재 상태: 소스 구현, Humble 빌드, 정책 49개 및 ROS 통합 3개 검사 통과. Foxy/실물 미검증.

## 변경 파일·함수

- [`control.py`](../unitree_go2_teleop/control.py): `Control.receive()` 속도 제한과 입력 검증, `Control.sample()` 입력 watchdog과 정지 재전송 구간, `request_fields()` 공식 API 형식 변환.
- [`bridge.py`](../unitree_go2_teleop/bridge.py): `SportBridge.on_twist()` / `tick()` / `send()` ROS 통신, `stop_before_shutdown()` 종료 정지, `main()` 종료 시그널 처리. ROS 시각과 독립적인 monotonic watchdog 및 steady timer 사용.
- [`package.xml`](../package.xml), [`setup.py`](../setup.py), [`setup.cfg`](../setup.cfg): ament_python 패키지와 `cmd_vel_to_sport` 실행 등록.
- [`test_control.py`](../test/test_control.py): 방향·제한·정지·NaN/Inf·설정 검증.
- [`test_ros_bridge.py`](../test/test_ros_bridge.py): 실제 ROS 메시지 왕복, dry-run 무발행, 정지 watchdog, 프로세스 종료 정지 검사.
- [`README.md`](../README.md): Foxy 설치, Wi-Fi SSH와 내부 DDS 구분, 두 터미널 실행, 키 조작.

## 검증

최초 구현 검사 당시 별도 `/home/a/unitree_go2_teleop_ws`에서 실행한 기록이다. 이후 [공식 workspace로 이관](2-cyclonedds-workspace-integration.md)했고 아래 재현 명령은 현재 위치로 갱신했다.

현재 PC는 ROS 2 Humble / Python 3.10이다. 최초 구현 시 기존 공식 소스 `/home/a/unitree_ros2`는 수정하지 않고 `unitree_api`를 이 workspace의 build/install로 별도 빌드했다. 공식 Foxy rclpy 소스에서 사용한 `ClockType.STEADY_TIME`, `create_timer(clock=...)`, QoS 이름을 확인했다. 이는 Foxy 실환경 시험을 대체하지 않는다.

- 제어 정책: 49개 테스트 통과.
- Humble colcon: `unitree_api`, `unitree_go2_teleop` 두 패키지 빌드 성공.
- 설치 검사에서 maintainer 이메일 `a@localhost`가 ROS manifest 검증에 실패해 일반 Python 패키지로 인식되는 문제를 발견했다. 유효한 예시 주소 `a@example.com`으로 고치고 `ros.ament_python` 인식 및 재빌드를 확인했다. 이 주소는 배포 전에 실제 관리자의 주소로 교체할 메타데이터이다.
- 최종 설치 확인: `ros2 pkg executables unitree_go2_teleop`에서 `unitree_go2_teleop cmd_vel_to_sport` 출력, 설치된 bridge 및 공식 Request import 성공.
- ROS 통합: localhost / domain 193 / 테스트 전용 토픽에서 3개 통과(2.53초). dry-run의 Unitree publisher 미생성, 실제 Request의 속도 제한·방향·API 번호, `/clock` 없는 `use_sim_time=true`에서도 watchdog 정지, SIGTERM 종료 전 정지 요청을 확인함.
- 검사 중 환경 오류: 공식 메시지 빌드 완료 전에 source한 경로 오류를 완료 후 workspace source로 해결. 샌드박스의 인터페이스 조회 차단은 승인된 외부 실행으로 해결. `ROS_LOCALHOST_ONLY=1`과 명시적 `lo`의 중복 오류는 `lo`만 선택해 해결.
- 로봇 이동 명령: 미실행.
- Foxy 빌드/실행, SSH 연결, 로봇 상태 수신, 실물 직진/후진/회전/정지: 대기.

정책 검사 재현:

```bash
cd ~/unitree_ros2/cyclonedds_ws
PYTHONPATH=src/unitree_go2_teleop /usr/bin/python3 -m pytest -q src/unitree_go2_teleop/test/test_control.py
```

로컬 ROS 통합 검사 재현(로봇용 설정으로 사용하지 않음):

```bash
cd ~/unitree_ros2/cyclonedds_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
export GO2_TELEOP_ROS_TEST=1
export ROS_DOMAIN_ID=193
export ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface name="lo"/></Interfaces></General></Domain></CycloneDDS>'
PYTHONPATH=src/unitree_go2_teleop:$PYTHONPATH /usr/bin/python3 -m pytest -q src/unitree_go2_teleop/test/test_ros_bridge.py
```

통합 검사는 `/go2_teleop_test/request`, `/go2_shutdown_test/request`만 사용하며 `/api/sport/request`에는 발행하지 않는다. 이 테스트 셸은 사용 후 닫고 로봇용 설정 셸과 분리한다.

로컬 제한은 위 CycloneDDS의 명시적인 `lo` 선택으로 적용한다. 현재 Humble에서는 `ROS_LOCALHOST_ONLY=1`과 `lo` 명시를 함께 사용하면 인터페이스 중복 선택 오류가 발생해 `ROS_LOCALHOST_ONLY=0`을 사용했다.

## 다음 실물 확인

1. SSH 사용자/IP와 로봇 내부 공식 ROS 2 패키지 위치를 확인한다.
2. Foxy 환경에서 빌드하고, 내부 DDS 인터페이스와 Sport 상태 수신을 확인한다.
3. dry-run에서 모든 기본 키와 입력 중단 정지를 확인한다.
4. 실제 Sport Mode에서 전진/후진, 제자리 회전, 곡선 주행을 각각 저속으로 확인한다.
5. 키 입력 중단 및 SSH 단절 시 정지 동작을 관찰하고 실측 결과를 별도 기록한다.

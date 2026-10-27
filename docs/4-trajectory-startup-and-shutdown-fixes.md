# 4. Trajectory 실행·종료 오류 수정

- 수정일: 2026-10-08 (Asia/Seoul)
- 범위: 현재 작업 중인 trajectory 변경을 보존하고 실행 오류, 종료 중 재주행,
  인자 실행 경로 및 설정값 검증을 수정했다.

## 코드 변경

- [timed_trajectory.py](../trajectory_control/trajectory_control/timed_trajectory.py)
  - `__init__`: `finished`를 초기화하고 `interactive` 모드를 추가했다.
    기본값 `true`는 기존 반복 입력, `false`는 ROS 인자 명령을 한 번 실행한다.
    단일 실행은 정지 반복을 완료한 뒤 노드를 종료한다.
  - `validate_command`: 터미널 입력, 시작 인자, 주행 시작 시 동일한 속도·시간
    검증을 적용한다. NaN/Inf, 0 이하 duration, 속도 제한 초과를 거부한다.
  - 설정값 검증: 발행 주기 5–100 Hz, PID gain 유한·0 이상,
    yaw 보정 상한 0–0.4 rad/s. 낮은 발행률이 Bridge의 0.5초 watchdog과
    충돌하지 않도록 제한했다.
  - `timer_callback`: 단일 실행의 완료, 대화형 입력 EOF를 처리한다.
    기존 초기 IMU 대기 3초, 주행 중 IMU 단절 0.5초 기준은 유지한다.
    타이머에는 monotonic 경과 시간과 일치하는 steady clock을 사용한다.
  - `stop_before_shutdown`, `main`: SIGINT/SIGTERM/SIGHUP에서 ROS context를
    유지한 채 타이머와 입력을 먼저 차단하고 0 명령을 5회 전송한다.
    종료 중 `spin_once`가 이동 명령을 다시 발행하던 경로를 제거했다.
    노드 생성 실패 시에도 context 종료와 signal handler 복원을 수행한다.
- [timed_trajectory.launch.py](../trajectory_control/launch/timed_trajectory.launch.py)
  - `generate_launch_description`: 미정의 `self` 호출을 제거했다.
  - `interactive:=true`에서는 기존 GNOME 터미널을 사용하며 `--wait`를 추가했다.
    `interactive:=false`는 터미널 없이 실행한다. 두 Node는 상호 배타적이다.
  - trajectory 노드에서 사용하지 않는 `request_topic` 전달을 제거했다.
    Bridge의 기존 실제 명령 발행 설정은 유지했다.
- [README](../README.md): 단일 실행, 데스크톱 반복 입력, SSH 두 터미널 실행,
  허용 파라미터 범위 및 단일 실행 후 Bridge가 대기하는 동작을 명시했다.

## 검증

- [회귀 테스트](../trajectory_control/test/test_timed_trajectory.py): **28개 통과**.
  - 잘못된 설정값 17개, 대화형 재입력, 단일 인자 실행과 종료,
    초기/주행 중 IMU 타임아웃, 새 heading 기준 대기, PID 방향과 제한,
    종료 중 대기 명령·타이머 차단, main 인터럽트와 초기화 실패, EOF 처리.
  - 실제 설치된 ROS launch 라이브러리로 launch 생성 및 두 모드 조건을 검증했다.
    Node 동작 검증은 ROS/DDS를 대체한 모의 객체를 사용했다.
- 실행 명령:

  ```bash
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
      trajectory_control/test/test_timed_trajectory.py
  ```

- 실물 명령 발행, DDS 통신, GNOME 터미널 표시, 로봇 내부 Foxy 빌드·주행은
  실행하지 않았다. 실제 구동 환경에서 별도 검증이 필요하다.
- 기존 변경 사항을 포함한 다른 패키지의 코드에는 손대지 않았다.

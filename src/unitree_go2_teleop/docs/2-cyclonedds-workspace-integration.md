# 2. 공식 cyclonedds_ws에 텔레옵 통합

- 수정일: 2026-09-10 (Asia/Seoul)
- 요청: 로봇에서 키보드·변환 패키지를 모두 공식 `unitree_ros2/cyclonedds_ws/src` 안에 넣어 빌드·실행.
- 현재 상태: 소스 이동, 실행 안내 수정, Humble 통합 workspace 빌드·실행 등록 검증 완료.

## 변경

- 기존 `/home/a/unitree_go2_teleop_ws/src/unitree_go2_teleop`의 패키지 소스를 이 문서의 상위 패키지 폴더로 이동했다. `Control.receive/sample`, `SportBridge` 등 제어 함수의 동작은 유지했다.
- 표준 키보드 소스를 형제 폴더 `teleop_twist_keyboard`로 배치했다. 원본: `https://github.com/ros2/teleop_twist_keyboard.git`, 태그 `2.3.2`, 커밋 `81e7e81e3a9879985d55d7ac136e0d538de42d6f`. 라이선스와 원본 소스를 유지했다.
- [`README.md`](../README.md)의 설치·빌드·source 경로를 공식 workspace 하나로 통일했다. 패키지 의존성 `unitree_api`, `teleop_twist_keyboard`는 같은 workspace에서 해석된다.
- 기존 별도 workspace에는 이관 안내와 `COLCON_IGNORE`를 남겼다. 과거 build/install/log는 보존하고 현재 실행에는 사용하지 않는다.
- 공식 저장소의 기존 `setup.sh` 수정과 DDS 소스는 보존했다.

## 검증

- 패키지 이동 전후 소스 9개 SHA-256 일치. 제어 함수 변경 없음. 문서 내부 로컬 링크 검증 통과.
- 공식 workspace에서 `unitree_api`, `teleop_twist_keyboard`, `unitree_go2_teleop` 3개 빌드 성공.
- 두 텔레옵 패키지 모두 `ros.ament_python`으로 인식. `ros2 pkg prefix`가 각각 `cyclonedds_ws/install/unitree_go2_teleop`, `cyclonedds_ws/install/teleop_twist_keyboard`를 반환했다.
- `ros2 pkg executables`에서 `unitree_go2_teleop cmd_vel_to_sport`, `teleop_twist_keyboard teleop_twist_keyboard` 확인. 두 모듈 및 공식 Request import 성공.
- 새 위치에서 정책 검사 49개 통과.
- 새 workspace의 `install/setup.bash`만 추가로 source하고 기존 workspace/PYTHONPATH 지정 없이 ROS 통합 검사 3개 통과(2.51초). localhost 전용 DDS/domain 193/테스트 토픽에서 dry-run 무발행, 속도 변환, watchdog 정지, SIGTERM 정지를 재확인했다. 총 52개 검사 통과.
- 빌드 경고: Humble에 이미 설치된 키보드 패키지를 이 workspace의 2.3.2 소스로 덮어 사용하는 overlay 경고와 표준 키보드 원본 `setup.cfg`의 오래된 하이픈 옵션 경고가 있었음. 빌드는 성공했고 설치 경로를 검증했다. 원본 키보드 소스는 수정하지 않았다.
- 로봇 Foxy와 실물 주행: 미실행. 현재 PC는 Humble이다.

실행 순서는 [패키지 안내](../README.md), 기존 제어 기능과 검사 항목은 [최초 구현 기록](1-basic-driving-and-turning.md)을 참조한다.

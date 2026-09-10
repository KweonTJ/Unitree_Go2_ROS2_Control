# 텔레옵 워크스페이스 이관 안내

2026-09-10에 소스를 공식 Unitree의 `cyclonedds_ws/src`로 이관했다.

- [현재 설치·실행 안내](../unitree_ros2/cyclonedds_ws/src/unitree_go2_teleop/README.md)
- [워크스페이스 통합 기록](../unitree_ros2/cyclonedds_ws/src/unitree_go2_teleop/docs/2-cyclonedds-workspace-integration.md)

이 디렉토리의 과거 build/install/log는 이전 검증 산출물이다. 현재 작업에는 `~/unitree_ros2/cyclonedds_ws`를 사용하며 이곳의 install 환경은 source하지 않는다. 이관 전 설치의 소스 링크는 더 이상 유효하지 않을 수 있다. `COLCON_IGNORE`는 상위 디렉토리를 탐색할 때 과거 workspace가 중복 발견되지 않도록 한다.

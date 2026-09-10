# 3. 원래 텔레옵 workspace에 코드 복사 복구

- 수정일: 2026-09-10 (Asia/Seoul)
- 요청: 이관이 아닌 복사 방식으로 사용하며 기존 `unitree_go2_teleop_ws`에 코드를 다시 보관.
- 변경: 공식 workspace의 두 텔레옵 패키지에서 소스·설정·테스트·문서 25개를 복사했다. 원본 위치는 유지했다.
- `COLCON_IGNORE`를 제거해 이 workspace를 다시 빌드할 수 있게 했다.
- 루트 `README.md`와 기존 기록 링크를 복구하고 PC 개발 소스 보존 및 로봇 `cyclonedds_ws/src`로 복사하는 절차를 명시했다.
- `Control`과 `SportBridge` 함수 및 키보드 제어 로직은 변경하지 않았다.

## 검증

- 복사 전후 25개 파일 SHA-256 일치, 공식 workspace 쪽 원본 보존 확인. 문서 로컬 링크 및 `COLCON_IGNORE` 제거 확인.
- 이 workspace에서 두 패키지 `ros.ament_python` 인식 및 Humble 빌드 성공.
- `ros2 pkg prefix`가 두 패키지 모두 `/home/a/unitree_go2_teleop_ws/install/` 아래를 반환했다. 두 실행 파일 등록 및 Python 모듈 import도 이 workspace의 build 경로에서 확인했다.
- 기존 제어 로직은 해시가 동일해 기능 테스트는 반복하지 않았다. 이전 검증 결과는 정책 49개와 ROS 통합 3개 통과이다.
- 표준 키보드 원본 설정의 하이픈 옵션 경고와 같은 패키지를 underlay 위에 사용하는 overlay 경고가 있었으나 빌드는 성공했다.
- 로봇 복사·Foxy 실행·실물 주행: 미실행.

[현재 사용 안내](../README.md)

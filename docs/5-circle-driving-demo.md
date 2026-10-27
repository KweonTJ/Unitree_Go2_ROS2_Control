# 5. 원형 주행 및 전방 라이다 정지 데모

- 수정일: 2026-10-27 (Asia/Seoul)
- 목적: 위치 인식 없이 일정 속도로 원형 주행하고 전방 물체가 사라질 때까지 정지.
- 추가 패키지: [`demo_test`](../demo_test/README.md).
- `demo_test/demo_test/control.py`: `CircleControl.observe`에서 전방 부채꼴·높이·거리
  조건을 검사한다. `command`는 입력 미수신·중단·물체 감지 시 0을 반환하며,
  clear 입력이 유지되면 기존 속도로 재개한다.
- `demo_test/demo_test/node.py`: `CircleNode`가 PointCloud2를 구독하고 Twist를
  발행한다. frame 불일치와 잘못된 입력에서 정지하며 종료 전 0을 반복 전송한다.
- `demo_test/launch/circle_test.launch.py`: 기존 Sport 브리지와 함께 실행하고
  거리·영역·속도·토픽을 실행 인자로 노출한다.
- 기존 사용자 변경과 기존 브리지 코드는 수정하지 않았다.
- 검증: 상태 및 입력 파라미터 단위 테스트 17개 통과. Humble의 실제
  PointCloud2 생성·디코딩으로 정지/재개 확인. 노드 import 및 launch 생성 확인.
- 미확인: 실물 주행, 기본 물체 인지 토픽 이름/타입, 센서 좌표축 및 높이 범위.
  `/utlidar/cloud` 및 `utlidar_lidar`는 확인 전 기본 가정이다.
- 빌드: colcon의 ament_python 패키지 인식은 확인했다. 빌드는 `Starting`
  이후 진행 출력 없이 대기해 중단했으며, 빌드 성공은 확인하지 못했다.

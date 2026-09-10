# Go2 텔레옵 개발·로봇 복사용 워크스페이스

2026-09-10: 사용자의 정정에 따라 이 workspace에 코드를 복원했다. **PC의 소스는 여기에 보관하고, 로봇에는 패키지 폴더를 복사한다. 이동하지 않는다.** 기존 PC `unitree_ros2/cyclonedds_ws/src`의 복사본도 유지한다. 두 위치는 독립된 파일이므로 변경 사항은 자동 동기화되지 않는다.

```text
unitree_go2_teleop_ws/
├── src/
│   ├── unitree_go2_teleop/     # 속도 변환·입력 watchdog
│   └── teleop_twist_keyboard/ # 표준 키보드 2.3.2
├── docs/
└── install/                  # 이 PC에서 빌드한 결과
```

## PC에서 빌드

현재 PC는 Humble이다. 공식 Unitree 메시지 환경을 먼저 불러온 뒤 이 workspace를 빌드한다.

```bash
source /opt/ros/humble/setup.bash
source ~/unitree_ros2/cyclonedds_ws/install/setup.bash
cd ~/unitree_go2_teleop_ws
colcon build --symlink-install --packages-select teleop_twist_keyboard unitree_go2_teleop
source install/setup.bash
ros2 pkg executables unitree_go2_teleop
ros2 pkg executables teleop_twist_keyboard
```

PC의 기본 변환 노드는 `dry_run=true`로 동작한다. 주행 키와 실행 명령은 [패키지 안내](src/unitree_go2_teleop/README.md)를 참조한다.

## 로봇에 복사

이 workspace의 `src/unitree_go2_teleop`, `src/teleop_twist_keyboard` 두 폴더를 로봇의 `~/unitree_ros2/cyclonedds_ws/src/` 안에 **복사**한다. PC 소스는 유지한다. PC의 `build/`, `install/`, `log/`는 로봇으로 가져가지 않는다.

로봇의 기존 공식 Foxy/DDS/메시지 설치가 완료된 상태에서:

```bash
source /opt/ros/foxy/setup.bash
source ~/unitree_ros2/cyclonedds_ws/install/setup.bash
cd ~/unitree_ros2/cyclonedds_ws
colcon build --symlink-install --packages-select teleop_twist_keyboard unitree_go2_teleop
source install/setup.bash
```

로봇에서는 이 `cyclonedds_ws` 하나로 키보드와 변환 노드를 실행한다. PC 개발 workspace와 로봇 실행 workspace의 위치가 다른 것은 의도한 구조다.

## 기록

- [최초 구현 기록](docs/1-basic-driving-and-turning.md)
- [복사 방식 복구 기록](docs/3-restore-copy-workspace.md)

패키지 내부의 기존 통합 기록은 당시 작업 이력이다. 현재 개발·배포 방식은 이 문서의 **PC 소스 보존 → 로봇 src로 복사**를 따른다.

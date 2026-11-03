#!/usr/bin/env bash
# 작성자: Git 이력 참조
# 작성목적: aws-style-diagram 저장소를 Claude Code와 Codex 스킬 폴더에 심볼릭 링크로 연결한다.
# 작성일: 2026-11-03
# 주의사항:
#   - 링크 방식이라 저장소를 고치거나 git pull 하면 두 도구에 바로 반영된다.
#   - 대상 경로에 링크가 아닌 실제 폴더가 있으면 덮어쓰지 않고 멈춘다.
#   - Codex 경로는 CODEX_HOME 이 있으면 그것을 따른다.
# 사용법: ./install.sh [--uninstall]
# 변경사항 내역:
# - 2026-11-03 | 최초 작성 | Claude Code, Codex 링크 설치와 제거
# - 2026-11-03 | 벡터 출력 | fontTools 설치 여부 안내 추가
set -euo pipefail

SKILL_NAME="aws-style-diagram"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOTS=(
  "${HOME}/.claude/skills"
  "${CODEX_HOME:-${HOME}/.codex}/skills"
)

uninstall=false
if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall=true
fi

for root in "${TARGET_ROOTS[@]}"; do
  target="${root}/${SKILL_NAME}"
  if [[ "${uninstall}" == true ]]; then
    if [[ -L "${target}" ]]; then
      rm "${target}"
      echo "제거: ${target}"
    fi
    continue
  fi

  mkdir -p "${root}"
  if [[ -e "${target}" && ! -L "${target}" ]]; then
    echo "중단: ${target} 에 링크가 아닌 폴더가 있습니다. 확인 후 직접 옮기거나 지워 주세요." >&2
    exit 1
  fi
  ln -sfn "${REPO_DIR}" "${target}"
  echo "연결: ${target} -> ${REPO_DIR}"
done

if [[ "${uninstall}" == false ]]; then
  command -v python3 >/dev/null || echo "참고: python3 이 없어 render.py 를 실행할 수 없습니다."
  python3 -c "import fontTools" 2>/dev/null || echo "참고: fontTools 가 없습니다. python3 -m pip install fonttools 로 설치하세요."
  if [[ -z "${CHROME_PATH:-}" && ! -e "/Applications/Google Chrome.app" ]] \
     && ! command -v google-chrome >/dev/null && ! command -v chromium >/dev/null; then
    echo "참고: Chrome 또는 Chromium 이 없어 PDF 와 PNG 는 만들지 못합니다(벡터 SVG 는 만듭니다). CHROME_PATH 로 경로를 줄 수 있습니다."
  fi
fi

# aws-style-diagram

Claude Code와 Codex에서 함께 쓰는 스킬이다. AWS 공식 아키텍처 아이콘 스타일로 시스템 구성도, 배포 구성도, CI/CD 그림을 그린다.
그림은 spec JSON 한 개로 정하고 `scripts/render.py`가 SVG, HTML, 3배 PNG를 만든 뒤 배치 검사를 돌린다.

![CI/CD 배포 구성도 예시](examples/out/ecs-cicd.png)

## 설치

```bash
git clone https://github.com/kgyujin/aws-style-diagram-skill.git ~/workspace/aws-style-diagram-skill
~/workspace/aws-style-diagram-skill/install.sh
```

`~/.claude/skills/aws-style-diagram`과 `~/.codex/skills/aws-style-diagram`(CODEX_HOME이 있으면 그 아래)에
같은 저장소를 가리키는 심볼릭 링크가 생긴다. `git pull`로 두 도구가 함께 갱신되고, `./install.sh --uninstall`로 링크를 지운다.

Claude Code에서는 `/aws-style-diagram`, Codex에서는 `$aws-style-diagram`으로 직접 부를 수도 있고,
"AWS 스타일로 구성도 그려줘"처럼 말해도 스킬 설명을 보고 골라 쓴다.

필요한 것: Python 3.9+, Google Chrome 또는 Chromium(PNG 찍기, 경로가 다르면 `CHROME_PATH`).

## 사용

```bash
python3 -I scripts/render.py examples/ecs-cicd.json out/      # 그리기 + 배치 검사
python3 -I scripts/render.py --icons rds                    # 아이콘 이름 찾기
python3 -I scripts/fetch_brand.py redis mongodb             # 기술 로고 더 받기
```

spec 형식과 그림 규칙은 [SKILL.md](SKILL.md), 배치 요령은 [references/layout-guide.md](references/layout-guide.md)에 있다.

## 폴더

| 폴더 | 내용 |
| --- | --- |
| `install.sh` | Claude Code, Codex 스킬 폴더에 링크 설치와 제거 |
| `scripts/` | `render.py`(그리기, 배치 검사), `fetch_brand.py`(기술 로고 받기), `fetch_aws_icons.sh`(AWS 아이콘 전체 패키지 받기) |
| `assets/aws/` | AWS Architecture Icons(2026-07-31) 서비스, 그룹, 일반 리소스 아이콘과 이름표 `index.json` |
| `assets/brands/` | Simple Icons 16.33.0 기술 로고와 색, 라이선스 `brands.json` |
| `examples/` | 서버리스, CI/CD 배포, 웹 3계층 spec과 결과 PNG |
| `references/` | 배치 가이드 |

## 아이콘 출처

[assets/NOTICE.md](assets/NOTICE.md)에 적었다. AWS 아이콘은 AWS가 허락한 대로 아키텍처 그림에만 쓰고,
기술 로고는 각 소유자의 상표다.

# aws-style-diagram

AWS 공식 아키텍처 아이콘 스타일로 시스템 구성도, 배포 구성도, CI/CD 그림을 그리는 에이전트 스킬이다.
그림은 spec JSON 한 개로 정하고 `scripts/render.py`가 SVG, HTML, 3배 PNG를 만든 뒤 배치 검사를 돌린다.

![CI/CD 배포 구성도 예시](examples/out/ecs-cicd.png)

## 설치

```bash
git clone https://github.com/kgyujin/aws-style-diagram-skill.git ~/.claude/skills/aws-style-diagram
```

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
| `scripts/` | `render.py`(그리기, 배치 검사), `fetch_brand.py`(기술 로고 받기), `fetch_aws_icons.sh`(AWS 아이콘 전체 패키지 받기) |
| `assets/aws/` | AWS Architecture Icons(2026-07-31) 서비스, 그룹, 일반 리소스 아이콘과 이름표 `index.json` |
| `assets/brands/` | Simple Icons 16.33.0 기술 로고와 색, 라이선스 `brands.json` |
| `examples/` | 서버리스, CI/CD 배포, 웹 3계층 spec과 결과 PNG |
| `references/` | 배치 가이드 |

## 아이콘 출처

[assets/NOTICE.md](assets/NOTICE.md)에 적었다. AWS 아이콘은 AWS가 허락한 대로 아키텍처 그림에만 쓰고,
기술 로고는 각 소유자의 상표다.

---
name: aws-style-diagram
description: AWS 공식 아키텍처 아이콘 스타일(AWS Cloud, Region, VPC, 서브넷, EKS 묶음 상자 + 정사각형 서비스 아이콘 + 아이콘 아래 이름)로 시스템 구성도, 배포 구성도, CI/CD 파이프라인 그림을 diagram-design식 편집 양식(역할 색, 강조 1~2곳, 둥근 직각 선, 띄운 라벨, 범례 띠, 4px 격자)으로 그려 확대해도 깨지지 않는 벡터 SVG와 PDF, PNG로 만든다. AWS가 아닌 기술(React, FastAPI, GitHub Actions, Argo CD, 쿠버네티스, OpenAI 등)도 같은 모양의 타일로 맞춘다. "AWS 아키텍처 다이어그램", "AWS 스타일로 그려줘", "구성도/배포 구성도/인프라 그림을 이 이미지처럼", "EKS, RDS, ECR 들어간 그림", "아키텍처정의서 그림 다시 그려줘", "GitHub Actions + ArgoCD 배포 흐름 그림" 같은 요청이면 클라우드 이름을 말하지 않아도 이 스킬을 쓴다. 문서(Word, PDF, 발표 자료)에 넣을 아키텍처 그림이 필요할 때도 쓴다.
---

# AWS 스타일 구성도

Claude Code와 Codex에서 같은 폴더를 함께 쓴다(`install.sh`가 두 스킬 폴더에 링크를 건다).

이 파일이 있는 폴더를 `SKILL`이라고 부른다. 그림은 spec JSON 한 개로 정하고 `scripts/render.py`로 그린다.
좌표는 직접 정하지만 연결점, 아이콘 타일, 라벨 바탕, 배치 검사는 스크립트가 맡는다.

```bash
SKILL="<이 SKILL.md가 있는 폴더의 절대경로>"
python3 -I "$SKILL/scripts/render.py" <spec.json> <출력폴더>     # 벡터 SVG, 벡터 PDF, PNG(3배) + 배치 검사
python3 -I "$SKILL/scripts/render.py" --icons rds                 # 아이콘 이름 찾기
python3 -I "$SKILL/scripts/fetch_brand.py" redis mongodb          # 없는 기술 로고 받기
```

필요한 것: Python 3.9+, fontTools(`python3 -m pip install fonttools`), Google Chrome 또는 Chromium(PDF와 PNG).
Chrome 경로가 다르면 `CHROME_PATH`로 준다.

## 양식

모든 그림은 같은 양식으로 나온다. [diagram-design](https://github.com/cathrynlavery/diagram-design)(MIT)의 편집 디자인 체계를
따르고, AWS 아이콘만 그대로 둔다.

- **색은 역할로만 쓴다.** 바탕 `paper #f5f5f5`, 글자와 테두리 `ink #2d3142`, 기본 선 `muted #4f5d75`, 부제와 라벨 `soft #5a6580`,
  강조 `accent #bf4520`, 외부 호출 `link #2e5aa8`. 다른 색을 새로 만들지 않는다.
- **강조는 1~2곳만.** 그림이 설명하려는 핵심 노드에 `"focal": true`를 준다. 3개 이상이면 배치 검사가 막는다.
  주 요청 흐름 선(`"kind": "primary"`)도 핵심 경로 하나에만 쓴다.
- **글꼴 세 가지.** 이름은 Geist SemiBold, 기술 값(포트, 서비스 이름, 영문 라벨)은 Geist Mono, 한글은 Pretendard로 이어 쓴다.
  영문 선 라벨과 영문 그룹 제목은 Mono 대문자에 자간을 주고, 한글은 sans 그대로 둔다.
- **선은 직각, 모서리는 둥글게.** 꺾이는 곳은 반지름 8로 둥글린다. 사선은 배치 검사가 막는다.
- **라벨은 선에서 띄운다.** 라벨은 선 위에 얹지 않고 가로 구간이면 위(아래), 세로 구간이면 오른쪽(왼쪽)에 8px 띄워 바탕색 상자를 깔고 놓는다.
- **범례는 아래 띠.** 쓰인 선 종류가 둘 이상이거나 focal이 있으면 그림 아래에 범례가 자동으로 붙는다(캔버스 높이 +56px).
- **4px 격자.** 캔버스, 그룹, 노드, 꺾이는 점, `at`은 모두 4의 배수로 쓴다. 노드 아이콘은 48px이라 가운데도 격자에 놓인다.
- **양이 적당해야 읽힌다.** 노드가 9개, 선이 12개를 넘으면 권고가 나온다. 넘으면 전체도와 상세도로 나누는 편이 낫다.
- **접근성.** SVG에 `role="img"`, `<title>`, `<desc>`가 들어간다. spec의 `title`, `desc`로 채우고, 없으면 이름과 개수로 채운다.

예전 AWS 공식 그룹 색(보라 VPC, 청록 서브넷 등)이 필요하면 spec에 `"theme": "aws"`를 준다. 문서 바탕이 흰색이라 회색 바탕이
어색하면 `"background": "white"`를 준다.

## 깨지지 않게 만드는 방법

결과 SVG에는 글꼴, 외부 파일, 내장 이미지가 하나도 없다. 그래서 어느 프로그램에서 열어도 같은 모양이고 확대해도 깨지지 않는다.

- **글자는 윤곽선으로 넣는다.** 함께 넣은 OFL 글꼴(Geist, Geist Mono, Pretendard)의 모양을 fontTools로 읽어 path로 바꾼다.
  보는 컴퓨터에 글꼴이 없어도 같은 글자로 보이고, 배치 검사도 실제 글자 폭으로 잰다.
- **아이콘은 벡터 그대로 펼친다.** `<image>`로 끼우지 않고 아이콘의 도형을 그룹으로 넣는다. 아이콘마다 id 앞머리를 달리해
  같은 id가 부딪혀 모양이 바뀌는 일을 막는다.
- **화살촉은 삼각형 도형, 반투명은 opacity 속성.** marker와 rgba를 쓰지 않아 이것을 잘 못 그리는 프로그램에서도 같다.
- **PDF도 벡터다.** 같은 SVG를 그림 크기에 맞춘 한 장짜리 PDF로 출력한다. 글꼴과 이미지가 들어가지 않는다.
- 글꼴에 없는 글자(예: 이모지)가 있으면 배치 검사가 알려 준다. 빈 상자로 나오기 때문에 다른 글자로 바꾼다.

문서에는 되도록 SVG나 PDF를 넣는다. Word와 PowerPoint(Microsoft 365, 2019 이상)는 SVG를 그대로 넣을 수 있고,
한글이나 예전 Office처럼 SVG를 못 넣는 곳에는 PDF나 PNG를 쓴다.

## 순서

1. **구성 요소와 연결을 근거에서 뽑는다.** 문서, 코드, 배포 설정에 있는 것만 그린다. 보기 좋게 하려고
   없는 서비스(예: CloudWatch, Secrets Manager, ALB)를 넣지 않는다. 확인 못 한 것은 그리지 않고 사용자에게 묻는다.
2. **배치를 정한다.** `references/layout-guide.md`를 읽는다. 바깥(사용자, 외부 시스템)과 안(AWS Cloud ▸ VPC ▸ EKS)을
   먼저 나누고, 요청이 흐르는 방향(왼쪽→오른쪽, 위→아래)으로 노드를 놓는다.
3. **spec JSON을 쓴다.** `examples/`에서 가장 가까운 것을 복사해 고친다. 결과 그림은 `examples/out/`에 있다.
   - `serverless.json`: 서버리스 구성도(Cognito, API Gateway, Lambda, S3, DynamoDB, CloudFront)
   - `ecs-cicd.json`: CI/CD 배포 구성도(GitHub Actions → ECR, ECS Fargate, 퍼블릭/프라이빗 서브넷)
   - `web3tier.json`: 리전, 퍼블릭/프라이빗 서브넷이 있는 웹 3계층(CloudFront, ALB, ECS, Aurora)
4. **그린다.** `render.py`가 끝에 배치 검사 결과를 출력한다. `문제 0건`이 될 때까지 좌표를 고친다.
   글자(이름, 라벨)를 바꿔서 검사를 통과시키지 않는다. 내용이 바뀌기 때문이다.
5. **PNG를 직접 열어 본다.** Claude Code는 Read, Codex는 이미지 보기 도구로 연다. 검사기가 잡지 못하는 어색함(선이 엉킴,
   라벨이 어느 선 것인지 헷갈림)은 눈으로 아래 체크리스트를 확인한다.
6. **문서에 넣는다.** 기존 docx 그림을 바꿀 때는 `references/layout-guide.md`의 'docx 그림 바꾸기'를 따른다.

## spec 쓰는 법

```json
{
  "name": "order",
  "title": "주문 처리 구성도",
  "canvas": {"width": 1100, "height": 640},
  "groups": [
    {"type": "aws-cloud", "x": 164, "y": 172, "w": 916, "h": 448, "title": "AWS Cloud"},
    {"type": "eks", "x": 216, "y": 252, "w": 820, "h": 200, "title": "Amazon EKS"}
  ],
  "nodes": [
    {"id": "api", "icon": "fastapi", "cx": 560, "top": 300, "label": "API 서버", "sub": "로그인, 탐색", "focal": true},
    {"id": "rds", "icon": "rds", "cx": 680, "top": 500, "label": "Amazon RDS", "sub": "PostgreSQL"}
  ],
  "edges": [
    {"path": ["api.b+20", [580, 524], "rds.l"], "label": "읽고 쓴다", "at": [580, 476], "kind": "primary"}
  ]
}
```

- **맨 위**: `name`(파일 이름), `title`과 `desc`(접근성용 제목과 한 문장 설명), `theme`(`editorial` 기본, `aws`),
  `background`(`white`면 흰 바탕), `legend`(`false`면 범례 없음, `{"primary": "주문 흐름"}`처럼 이름 바꾸기).
- **groups**: 뒤에 쓴 것이 위에 그려진다. 큰 묶음부터 쓴다. `type`:
  `aws-cloud`, `region`(점선), `vpc`, `private-subnet`, `public-subnet`, `account`, `eks`(점선),
  `auto-scaling`, `datacenter`, `box`(실선), `box-dashed`(점선, 외부 서비스나 묶음용).
  `icon`으로 머리 아이콘을 바꿀 수 있다. 제목이 영문이면 Mono 대문자, 한글이면 sans로 나온다.
- **nodes**: `cx`는 아이콘 가운데 x, `top`은 아이콘 위 y다. 노드 한 개는 폭이 이름/부제 길이만큼, 높이가 96px이다
  (아이콘 48 + 이름 + 부제). `icon`은 AWS 이름(`eks`, `ecr`, `rds`, `s3`, `lambda`, `users`, `office`, `client` 등)이나
  기술 로고 이름(`react`, `fastapi`, `githubactions`, `argo`, `kubernetes` 등)이다. 같은 이름이 둘 다 있으면 AWS가 먼저다.
  `brand:이름`, `aws:이름`으로 정할 수 있다. `focal: true`면 강조 상자로 감싸고 선은 그 상자 테두리에서 끝난다.
- **edges**: `path`는 점 목록이다. 점은 `[x, y]`나 연결점 문자열이다.
  - `id.l` / `id.r`: 아이콘 왼쪽/오른쪽 가운데(아이콘에서 4px). `id.t`: 아이콘 위. `id.b`: 부제 아래.
  - `+N`/`-N`: t/b는 x를, l/r은 y를 N만큼 옮긴다. 한 면에서 선 두 개가 나가면 24px 이상 벌린다.
  - 직각으로만 꺾는다. 꺾이는 점은 `[x, y]`로 넣는다. 모서리는 자동으로 둥글어진다.
  - `kind`: `default`(기본 회색), `primary`(주 요청 흐름, 강조색), `link`(외부 호출, API, 파랑). 예전 `bold: true`는 `primary`와 같다.
  - `style: "dashed"`(비동기, 가끔 쓰는 흐름), `both: true`(양방향).
  - `label`(줄바꿈은 `\n`), `at`(라벨을 붙일 구간 근처의 점, 없으면 가장 긴 구간 가운데),
    `labelSide`(`above` 기본, `below`, 세로 구간은 `right` 기본, `left`).
  - 선이 묶음 상자(예: 서비스 컨테이너)를 가리킬 때는 끝점을 상자 테두리 2px 앞 `[x, y]`로 준다.

## 그림 규칙 (이유가 있는 것들)

- **캔버스 폭 1100px.** A4 본문 폭(약 16cm)에 넣었을 때 노드 이름(17px)과 라벨(14px)이 9~10pt로 읽힌다.
  폭을 1400 이상으로 잡으면 문서에서 글자가 6pt 아래로 내려가 '깨져 보인다'는 말을 듣는다. 넓히지 말고 높이를 늘린다.
- **AWS 서비스는 공식 아이콘을 바꾸지 않는다.** 색, 모양, 비율이 AWS 아이콘 사용 조건이다.
- **AWS가 아닌 기술은 브랜드색 정사각형 + 흰 글리프로 통일한다.** 흰 글리프와 대비가 낮은 브랜드색(예: React 하늘색)은
  어두운 바탕에 브랜드색 글리프로 자동으로 바뀐다. 그래야 한 그림 안에서 아이콘 모양이 같아 보인다.
- **사람, 건물, 문서 같은 것은 AWS 일반 리소스 아이콘(선 아이콘)을 쓴다.** 묶음 바깥에 둔다.
- **라벨 자리는 `at`과 `labelSide`로 고른다.** 라벨은 선에서 띄워 놓이므로 옆 노드, 다른 선, 그룹 테두리에 닿지 않는 구간을 고른다.
- **점선 화살표는 '가끔 쓰는 흐름'**(평가, 설정 읽기, 이미지 가져오기), 강조색 선은 '주 요청 흐름', 파란 선은 '외부 호출'이다.
  범례에도 그렇게 나오고 그림 설명에도 그렇게 적는다.

## 체크리스트 (PNG를 열어 확인)

- [ ] 배치 검사 `문제 0건`
- [ ] 선이 아이콘, 이름, 그룹 제목을 지나지 않는다. 선끼리 겹쳐 달리지 않는다(교차는 꼭 필요할 때 한 번까지)
- [ ] 라벨이 자기 선 옆에 있고 어느 선의 라벨인지 헷갈리지 않는다
- [ ] 노드가 그룹 테두리에 걸치지 않는다(어느 그룹 소속인지 분명하다)
- [ ] 화살촉 방향이 실제 요청/데이터 방향과 같다
- [ ] 강조(focal, 주 요청 흐름)가 정말 핵심인 1~2곳에만 있다
- [ ] 범례에 쓰인 선 종류만 있다
- [ ] 근거 문서에 없는 구성 요소가 없다
- [ ] 문서에 넣었다면 SVG나 PDF로 넣었는지, 문서 PDF를 뽑아 실제 크기로 글자가 읽히는지 본다

## 아이콘과 라이선스

- `assets/aws/`: AWS Architecture Icons(2026-07-31 릴리스) 서비스 64px, 그룹, 일반 리소스(밝은 배경용).
  AWS는 이 아이콘을 아키텍처 그림을 만드는 데 쓰도록 허락한다. 아이콘을 고치거나 다른 회사 로고처럼 쓰지 않는다.
  전체 패키지(다른 크기, 어두운 배경용)는 `scripts/fetch_aws_icons.sh`로 받는다.
- `assets/fonts/`: Geist 1.9.0 Regular, Medium, SemiBold와 Geist Mono Regular, Medium(`OFL-Geist.txt`),
  Pretendard 1.3.9 Regular, Medium, SemiBold(`OFL-Pretendard.txt`). 모두 SIL Open Font License 1.1이고 글자를 윤곽선으로 바꿀 때만 쓴다.
- `assets/brands/`: Simple Icons 16.33.0 글리프(대부분 CC0). 색과 라이선스는 `brands.json`에 있다.
  CC0는 그림 파일 저작권만 푸는 것이고 상표 사용 허락은 아니다. 공개 발표 전에는 `guidelines` 주소를 읽는다.
- 새 로고는 `fetch_brand.py`로만 넣는다. 손으로 받은 SVG는 출처와 라이선스가 남지 않는다.
- 라이선스를 확인하지 못한 로고나 사내 로고는 `--local`을 붙여 `~/.config/aws-style-diagram/brands`에 넣는다
  (`AWS_STYLE_DIAGRAM_BRANDS`로 바꿀 수 있다). 저장소에 올라가지 않고 `render.py`가 함께 읽는다.

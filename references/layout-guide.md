# 배치 가이드

AWS 스타일 구성도를 실제로 그려 보며 통했던 방법이다. 좌표를 정하기 전에 한 번 읽는다.

## 1. 큰 틀

- **바깥 → 안 순서로 상자를 정한다.** 사용자와 외부 시스템(물류 시스템, GitHub)은 AWS Cloud 밖 왼쪽이나 위에,
  외부 API(OpenAI, Stripe 같은 SaaS)는 위쪽 `box-dashed` '외부 서비스' 묶음에 둔다.
- **AWS 안은 AWS Cloud ▸ VPC ▸ (EKS 또는 서브넷) 순으로 넣는다.** 상자 사이 여백은 20~25px, 머리 줄(아이콘 30px)
  아래로 첫 노드까지 40px 이상 둔다.
- **관리형 서비스 자리.** ECR, S3 같은 리전 서비스는 VPC 밖 AWS Cloud 안에, RDS는 VPC 안 클러스터 밖에 둔다.
  'DB는 쿠버네티스 밖' 같은 결정이 그림에서 바로 보인다.
- **주 흐름을 한 줄로.** 사용자 → 화면 → API 서버처럼 주 요청 흐름은 같은 높이(icon 가운데 y)에 놓아 직선으로 잇는다.

## 2. 노드 간격

- 노드 높이는 100px(아이콘 52 + 이름 + 부제). 위아래 노드 사이는 150px 이상 띄운다(라벨 들어갈 자리).
- 좌우 간격은 `부제 폭 + 30` 이상. 부제는 14px 기준 한글 한 글자 14px, 영문 8px로 어림한다.
  부제가 길면(18자 이상) 줄이거나 노드 간격을 넓힌다.
- 묶음 상자 오른쪽/왼쪽 끝 노드는 부제 끝이 테두리에서 10px 이상 떨어지게 한다.

## 3. 선 길 잡기

- **아래쪽 연결점(`.b`)은 부제 아래에서 나간다.** 이름 글자를 뚫지 않는다. 위쪽(`.t`)은 아이콘 바로 위다.
- **한 노드에 선이 많으면 면을 나눈다.** 들어오는 주 요청은 왼쪽, 외부 API 호출은 위, DB는 아래로 보낸다.
  같은 면에서 두 선이 나가면 `+25`처럼 25~30px 벌린다.
- **엇갈림을 피하는 법.** 위로 가는 선과 옆으로 가는 선이 엇갈리면, 옆으로 가는 선을 두 상자 테두리 사이
  여백 높이(예: VPC 위 테두리와 EKS 위 테두리 사이)로 지나게 한다.
- **여러 노드로 가는 선은 묶음 상자 하나로 받는다.** 예: GitHub Actions → 'ECS 서비스' 상자. 노드마다 선을 그리면
  선이 엉킨다.
- **같은 목적지로 가는 두 선은 다른 면으로 받는다.** 예: API → RDS 왼쪽, 워커 → RDS 오른쪽, 배치 → RDS 아래.

## 4. 라벨

- 라벨은 짧은 동사구로 쓴다(예: '읽고 쓴다', '이미지 올리기', '바뀐 설정 확인'). 한 줄 10자 안팎.
- 수평선 라벨은 선 위 가운데, 수직선 라벨은 선 위에 흰 바탕으로 얹거나 선 오른쪽 15px에 둔다.
- 짧은 선(100px 안쪽)에는 라벨을 선 위쪽 20px에 두거나 `\n`으로 두 줄로 나눈다.
- 그룹 머리 글자, 다른 선, 아이콘 위에 두지 않는다. 검사기가 잡는다.

## 5. 자주 쓰는 패턴

### 서버리스 구성도 (`examples/serverless.json`)
- VPC가 없으므로 AWS Cloud ▸ 리전 두 겹만 둔다. 사용자는 왼쪽 바깥에 한 개만 두고, 위(로그인), 가운데(주 요청),
  아래(조회)로 선을 나눠 보낸다.
- 주 요청 흐름(API Gateway → 함수 → 버킷 → 함수)은 한 줄에 놓고, 부수 저장소(DynamoDB, 썸네일 버킷)는 그 아래 줄에 둔다.
- 이벤트로 이어지는 흐름(버킷 업로드 → 함수)은 점선으로 그려 요청 흐름과 구분한다.

### CI/CD 배포 구성도 (`examples/ecs-cicd.json`)
- 위: GitHub 묶음(코드 저장소 → GitHub Actions). Actions는 아래로 ECR에 이미지를 올리고, 오른쪽으로 길게 돌아
  ECS 서비스 묶음 위로 배포 선을 내린다.
- 왼쪽 열(VPC 밖): ECR, Secrets Manager, CloudWatch. 각 서비스에서 ECS 서비스 묶음 왼쪽 테두리로 점선을 보낸다.
- VPC 안: 퍼블릭 서브넷에 ALB, 프라이빗 서브넷에 ECS 서비스 묶음과 DB. 여러 작업으로 가는 선은 묶음 상자 하나로 받는다.

### 웹 3계층 (`examples/web3tier.json`)
- 리전 ▸ VPC ▸ 퍼블릭/프라이빗 서브넷을 왼쪽에서 오른쪽으로 펼치고, CloudFront와 S3는 VPC 밖 리전 안에 둔다.

## 6. docx 그림 바꾸기 (python-docx)

기존 문서의 그림 자리와 크기 비율을 유지하며 이미지만 바꾼다. 폭은 그대로 두고 높이만 새 비율로 맞춘다.

```python
import docx
from docx.oxml.ns import qn
from PIL import Image

d = docx.Document("in.docx")
cell = d.tables[3].rows[0].cells[0]          # 그림이 든 칸(문서마다 다르다)
pngs = ["system.png", "deploy.png"]           # 칸 안 그림 순서대로
for blip, png in zip(cell._tc.xpath('.//a:blip'), pngs):
    d.part.related_parts[blip.get(qn('r:embed'))]._blob = open(png, 'rb').read()
for inline, png in zip(cell._tc.xpath('.//wp:inline'), pngs):
    w, h = Image.open(png).size
    ext = inline.find(qn('wp:extent'))
    cy = int(int(ext.get('cx')) * h / w)
    ext.set('cy', str(cy))
    for e in inline.xpath('.//a:ext'):
        e.set('cy', str(cy))
d.save("out.docx")
```

넣은 뒤에는 Word(또는 LibreOffice)로 PDF를 뽑아 실제 크기에서 글자가 읽히는지 확인한다.

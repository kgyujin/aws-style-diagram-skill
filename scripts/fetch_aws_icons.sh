#!/bin/sh
# AWS Architecture Icons 전체 패키지(2026-07-31 릴리스)를 받아 <출력폴더>에 푼다.
# 이 스킬의 assets/aws/에는 서비스 64px, 그룹, 일반 리소스(밝은 배경용)만 들어 있다.
# 다른 크기나 어두운 배경용이 필요할 때만 쓴다. 최신 패키지 주소는 https://aws.amazon.com/architecture/icons/ 에서 확인한다.
set -eu
OUT="${1:?사용: fetch_aws_icons.sh <출력폴더>}"
URL="https://d1.awsstatic.com/onedam/marketing-channels/website/public/shared/architecture-icon-release/Icon-package_07312026.5846e92413caa21490223536cc97f1269e44fa92.zip"
SHA="d2d166c453526471749d520e0db022c459abef759d2946cf2dd1d1c992dc6526"
mkdir -p "$OUT"
curl -fL --max-time 300 -o "$OUT/aws-icons.zip" "$URL"
echo "$SHA  $OUT/aws-icons.zip" | shasum -a 256 -c -
unzip -q -o "$OUT/aws-icons.zip" -d "$OUT" -x "__MACOSX/*"
echo "풀었다: $OUT"

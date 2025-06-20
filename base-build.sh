#!/bin/bash
IMAGE_NAME="sk-team-09-ai-base"
VERSION="1.0.0"

# Docker 이미지 빌드
docker buildx build \
  --tag ${IMAGE_NAME}:${VERSION} \
  --file Dockerfile.base \
  --platform linux/amd64 \
  ${IS_CACHE} .

#!/bin/sh
# Call this to build and push the repository to Docker Hub with the current
# Pygin version.

VERSION=$(python3 -m src.meta.agent)

docker build -t unrdeaddrop/pygin:${VERSION} .
docker push unrdeaddrop/pygin:${VERSION}
#!/bin/sh

# Start the build container (note that because the build container is named,
# you can't have multiple of these running at once). This should execute
# everything needed to generate the files below.
docker compose -f docker-compose-payload.yml up 

# Copy all of the results out of the container once it's exited.  Pygin's
# container name is pygin_build.
docker cp pygin_build:/app/agent_cfg.json ./agent_cfg.json
docker cp pygin_build:/app/payload.zip ./payload.zip
docker cp pygin_build:/app/payload-logs.txt ./payload-logs.txt


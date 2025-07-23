#!/usr/bin/env bash
# A 5-second delay can sometimes help ensure the desktop is fully ready
sleep 5

# Run the docker container
docker run --rm -it \
  --device=/dev/dri:/dev/dri \
  -v /sys:/sys:ro \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  hwmonitor

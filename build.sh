#!/bin/sh

d=$(date '+%Y%m%d%H%M%S')

docker build -t registry.leviathan.lan/panasonic-viera-mqtt:latest -t registry.leviathan.lan/panasonic-viera-mqtt:$d .
docker push registry.leviathan.lan/panasonic-viera-mqtt:latest
docker push registry.leviathan.lan/panasonic-viera-mqtt:$d
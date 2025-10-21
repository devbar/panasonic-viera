#!/bin/sh

docker build -t registry.leviathan.lan/panasonic-viera-mqtt:latest .
docker push registry.leviathan.lan/panasonic-viera-mqtt:latest
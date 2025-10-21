# Panasonic Viera TV Control AI Instructions

## Architectural Patterns

1. **Command Execution**
- Register new TV operations in `__main__.py` following:
```python
runner.command("volume_up", remote_control.volume_up)
```
- Maintain error handling consistency using `MSG_TV_SWITCHED_OFF`

2. **Service Boundaries**
- CLI: `__main__.py`
- MQTT Bridge: `mqtt_remote_service.py`
- Systemd: `systemd/panasonic-mqtt-remote.service`

## Development Workflows

```bash
# Build Docker image with TV control services
./build.sh --target docker

# Start debug console
python3 -m panasonic_viera <tv_ip> --verbose
```

## Key Conventions

- **Error Handling**: Always catch:
```python
(socket.timeout, TimeoutError, OSError)
```
- **CLI Structure**: Add new commands via `argparse` in `main()`
- **Logging**: Enable debug with `--verbose` flag

## Integration Points

- MQTT Topics:
  - Commands: `panasonic/viera/{tv_ip}/command`
  - Status: `panasonic/viera/{tv_ip}/status`

## Contribution Guidelines

1. Validate against:
```python
panasonic_viera.RemoteControl(<host>, <port>).get_volume()
```
2. Update systemd service file for new dependencies
3. Maintain Docker image parity with CLI features
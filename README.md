# rs485-modbus-sensor-test

Small command-line scripts for checking RS-485 / Modbus RTU sensors from a PC. Each script probes the supported sensors, then prints readings in a loop.

| Script | Measures | Supported sensors |
|---|---|---|
| `liquid_level_test.py` | Liquid level | Seeed Studio, Keller |
| `moisture_test.py` | Soil moisture | Seeed Studio, DFRobot |

> Not affiliated with or endorsed by Seeed Studio, Keller or DFRobot. Product names are trademarks of their respective owners and are used here only to say which sensors the scripts work with.

## Requirements

- Python 3.8+
- A USB-to-RS-485 adapter, with the sensor's A/B lines wired to it and the sensor powered as its datasheet specifies
- `pip install -r requirements.txt`

## Usage

```bash
# Liquid level: auto-detect the sensor, read forever
python liquid_level_test.py --port COM3
python liquid_level_test.py --port /dev/ttyUSB0 --sensor keller --interval 2 --count 10

# Soil moisture
python moisture_test.py --port COM11
python moisture_test.py --port COM11 --sensor dfrobot --count 10 --interval 2
python moisture_test.py --port COM11 --sensor seeedstudio --address 0x12 --baud 9600

# Scan an address range if you are not sure of the sensor's address
python moisture_test.py --port COM11 --scan 0x01-0x20 --debug
```

Press Ctrl+C to stop. The scripts exit with status 1 if no sensor responds.

### Options

| Option | Default | Scripts | Meaning |
|---|---|---|---|
| `--port` | required | both | Serial port (`COM3`, `/dev/ttyUSB0`, ...) |
| `--sensor` | `auto` | both | Sensor profile to use |
| `--interval` | `1.0` | both | Seconds between readings |
| `--count` | `0` | both | Number of readings, `0` = forever |
| `--baud` | `9600` | both | Baud rate |
| `--timeout` | `3.0` / `1.0` | liquid / moisture | Read timeout in seconds |
| `--address`, `--register`, `--scan`, `--parity`, `--stopbits`, `--debug` | | moisture only | Override defaults and debug |

Serial format is 8 data bits, no parity and 1 stop bit unless you change it.

## Sensor profiles

| Sensor | Script | Slave address | Register(s) | Reading |
|---|---|---|---|---|
| Seeed Studio | liquid level | `0x1A` | `0x0004` (1 reg) | millimetres, shown in 0.1 mm units |
| Keller | liquid level | `0x01` | `0x0022` (2 regs) | 32-bit signed pressure in 10^-5 bar, converted to mm of water column (0.1 mm units) |
| Seeed Studio | moisture | `0x12` | `0x0001` | raw value |
| DFRobot | moisture | `0x01` | `0x0000` | raw value x 10 |

These are the defaults the scripts use. Check your sensor's datasheet if yours differs.

## License

MIT, see [LICENSE](LICENSE).

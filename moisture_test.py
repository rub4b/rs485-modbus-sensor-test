#!/usr/bin/env python3
"""
Soil Moisture Sensor Test Script
Supports: Seeed Studio (addr 0x12) and DFRobot (addr 0x01) via Modbus RTU over RS-485.

Install: pip install minimalmodbus

Usage:
    python moisture_test.py --port COM11
    python moisture_test.py --port COM11 --sensor dfrobot --count 10 --interval 2
    python moisture_test.py --port COM11 --sensor seeedstudio --address 0x12 --baud 9600
    python moisture_test.py --port COM11 --scan 0x01-0x20 --debug
"""

import argparse
import sys
import time
import minimalmodbus

SENSORS = {
    "seeedstudio": {
        "name":     "Seeed Studio",
        "address":  0x12,
        "register": 0x0001,
        "convert":  lambda raw: raw,
    },
    "dfrobot": {
        "name":     "DFRobot",
        "address":  0x01,
        "register": 0x0000,
        "convert":  lambda raw: raw * 10,   # scale raw reading by 10
    },
}


PARITY_MAP = {
    "N": minimalmodbus.serial.PARITY_NONE,
    "E": minimalmodbus.serial.PARITY_EVEN,
    "O": minimalmodbus.serial.PARITY_ODD,
}


def parse_int(value):
    try:
        return int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid integer value: {value}") from exc


def parse_address_list(value):
    addresses = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", 1)
            start = parse_int(start_text.strip())
            end = parse_int(end_text.strip())
            if start > end:
                raise argparse.ArgumentTypeError(f"Invalid range: {part}")
            addresses.extend(range(start, end + 1))
        else:
            addresses.append(parse_int(part))
    if not addresses:
        raise argparse.ArgumentTypeError("No addresses specified")
    return sorted(set(addresses))


def make_instrument(port, address, baudrate, parity, stopbits, timeout, debug):
    inst = minimalmodbus.Instrument(port, address)
    inst.serial.baudrate = baudrate
    inst.serial.bytesize = 8
    inst.serial.parity   = PARITY_MAP[parity.upper()]
    inst.serial.stopbits = stopbits
    inst.serial.timeout  = timeout
    inst.mode            = minimalmodbus.MODE_RTU
    inst.debug           = debug
    return inst


def probe(port, sensor_key, baudrate, parity, stopbits, timeout, debug, address_override=None, register_override=None):
    sensor = SENSORS[sensor_key]
    address = sensor["address"] if address_override is None else address_override
    register = sensor["register"] if register_override is None else register_override
    try:
        inst  = make_instrument(port, address, baudrate, parity, stopbits, timeout, debug)
        raw   = inst.read_register(register, functioncode=3)
        value = sensor["convert"](raw)
        print(f"  OK  {sensor['name']} (addr=0x{address:02X}, reg=0x{register:04X}, raw={raw}, moisture={value})")
        return inst, {**sensor, "address": address, "register": register}
    except Exception as exc:
        msg = f"  --  {sensor['name']} not found (addr=0x{address:02X}, reg=0x{register:04X})"
        if debug:
            msg = f"{msg} ({exc})"
        print(msg)
        return None, None


def scan_addresses(port, addresses, profiles, baudrate, parity, stopbits, timeout, debug):
    for address in addresses:
        for profile in profiles:
            try:
                inst = make_instrument(port, address, baudrate, parity, stopbits, timeout, debug)
                raw = inst.read_register(profile["register"], functioncode=3)
                value = profile["convert"](raw)
                sensor = {
                    "name": profile["name"],
                    "address": address,
                    "register": profile["register"],
                    "convert": profile["convert"],
                }
                print(f"  OK  {sensor['name']} (addr=0x{address:02X}, reg=0x{sensor['register']:04X}, raw={raw}, moisture={value})")
                return inst, sensor
            except Exception as exc:
                if debug:
                    print(f"  --  addr=0x{address:02X} reg=0x{profile['register']:04X} no response ({exc})")
    return None, None


def read_loop(inst, sensor, count, interval):
    print(f"\nReading {sensor['name']} | interval={interval}s | count={'infinite' if count == 0 else count}\n")
    i = 0
    try:
        while count == 0 or i < count:
            i += 1
            try:
                raw      = inst.read_register(sensor["register"], functioncode=3)
                moisture = sensor["convert"](raw)
                print(f"[{time.strftime('%H:%M:%S')}] #{i:>4}  raw={raw:>5}  moisture={moisture:>6}")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Read error: {e}")
            if count == 0 or i < count:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",     required=True)
    parser.add_argument("--sensor",   choices=list(SENSORS) + ["auto"], default="auto")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--count",    type=int,   default=0, help="0 = infinite")
    parser.add_argument("--address",  type=parse_int, help="Override sensor address (decimal or hex, e.g., 0x12)")
    parser.add_argument("--register", type=parse_int, help="Override register (decimal or hex)")
    parser.add_argument("--scan",     type=parse_address_list, help="Scan address range/list (e.g., 1-20 or 0x10,0x11)")
    parser.add_argument("--baud",     type=int,   default=9600)
    parser.add_argument("--parity",   choices=["N", "E", "O", "n", "e", "o"], default="N")
    parser.add_argument("--stopbits", type=int,   choices=[1, 2], default=1)
    parser.add_argument("--timeout",  type=float, default=1.0)
    parser.add_argument("--debug",    action="store_true")
    args = parser.parse_args()

    print(
        f"\nProbing sensors on {args.port} "
        f"(baud={args.baud}, parity={args.parity.upper()}, stopbits={args.stopbits}, timeout={args.timeout}s)..."
    )

    inst, sensor = None, None
    if args.scan:
        if args.sensor == "auto" and args.register is None:
            profiles = [
                {"name": SENSORS["seeedstudio"]["name"], "register": SENSORS["seeedstudio"]["register"], "convert": SENSORS["seeedstudio"]["convert"]},
                {"name": SENSORS["dfrobot"]["name"], "register": SENSORS["dfrobot"]["register"], "convert": SENSORS["dfrobot"]["convert"]},
            ]
        elif args.sensor == "auto":
            profiles = [{"name": "Generic", "register": args.register, "convert": lambda raw: raw}]
        else:
            sensor_def = SENSORS[args.sensor]
            register = sensor_def["register"] if args.register is None else args.register
            profiles = [{"name": sensor_def["name"], "register": register, "convert": sensor_def["convert"]}]
        inst, sensor = scan_addresses(
            args.port, args.scan, profiles, args.baud, args.parity, args.stopbits, args.timeout, args.debug
        )
    elif args.sensor == "auto":
        for key in SENSORS:
            inst, sensor = probe(
                args.port, key, args.baud, args.parity, args.stopbits, args.timeout, args.debug,
                address_override=args.address, register_override=args.register
            )
            if inst:
                break
    else:
        inst, sensor = probe(
            args.port, args.sensor, args.baud, args.parity, args.stopbits, args.timeout, args.debug,
            address_override=args.address, register_override=args.register
        )

    if inst is None:
        print("\nNo sensor found. Check port, address, RS-485 adapter, and 12V power.")
        sys.exit(1)

    read_loop(inst, sensor, args.count, args.interval)


if __name__ == "__main__":
    main()

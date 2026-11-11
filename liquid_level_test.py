#!/usr/bin/env python3
"""
Liquid Level Sensor Test Script
Supports: Seeed Studio (addr=0x1A) and Keller (addr=0x01) via Modbus RTU over RS-485.

Install: pip install minimalmodbus
Usage:   python liquid_level_test.py --port COM3
         python liquid_level_test.py --port COM3 --sensor keller --interval 2
         python liquid_level_test.py --port /dev/ttyUSB0 --baud 9600 --timeout 1.5
"""

import argparse, time, sys, struct
import minimalmodbus

SENSORS = {
    "seeedstudio": {
        "name":       "Seeed Studio",
        "address":    0x1A,   # 26
        "register":   0x0004,
        "num_regs":   1,
        "convert":    lambda regs: max(regs[0], 0) * 10,   # mm -> 0.1 mm units
        "units":      "0.1mm",
    },
    "keller": {
        "name":       "Keller",
        "address":    0x01,
        "register":   0x0022,
        "num_regs":   2,
        # 2 registers = 32-bit signed int in 10^-5 bar; convert to 0.1 mm water column:
        #   level_0.1mm = (pressure_1e-5bar * 10197 + 5000) / 10000
        # (1 bar ~= 10197 mm H2O; the +5000 rounds to the nearest integer)
        "convert":    lambda regs: max(int((struct.unpack('>i', struct.pack('>HH', regs[0], regs[1]))[0] * 10197 + 5000) / 10000), 0),
        "units":      "0.1mm",
    },
}


def make_instrument(port, address, baudrate, timeout):
    inst = minimalmodbus.Instrument(port, address)
    inst.serial.baudrate = baudrate
    inst.serial.bytesize = 8
    inst.serial.parity   = minimalmodbus.serial.PARITY_NONE
    inst.serial.stopbits = 1
    inst.serial.timeout  = timeout
    inst.mode            = minimalmodbus.MODE_RTU
    return inst


def probe(port, key, baudrate, timeout):
    s = SENSORS[key]
    try:
        inst = make_instrument(port, s["address"], baudrate, timeout)
        regs = inst.read_registers(s["register"], s["num_regs"], functioncode=3)
        val  = s["convert"](regs)
        print(f"  OK  {s['name']} (addr=0x{s['address']:02X}, raw={regs}, {val} {s['units']})")
        return inst, s
    except Exception:
        print(f"  --  {s['name']} not found (addr=0x{s['address']:02X})")
        return None, None


def read_loop(inst, sensor, count, interval):
    print(f"\nReading {sensor['name']} | interval={interval}s | count={'infinite' if count == 0 else count}\n")
    i = 0
    try:
        while count == 0 or i < count:
            i += 1
            try:
                regs = inst.read_registers(sensor["register"], sensor["num_regs"], functioncode=3)
                val  = sensor["convert"](regs)
                mm   = val / 10.0
                print(f"[{time.strftime('%H:%M:%S')}] #{i:>4}  raw={regs}  level={val} {sensor['units']}  ({mm:.1f} mm)")
            except Exception as e:
                print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
            if count == 0 or i < count:
                time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


def main():
    parser = argparse.ArgumentParser(description="Probe and read RS-485 Modbus liquid level sensors.")
    parser.add_argument("--port",     required=True, help="Serial port, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("--sensor",   choices=list(SENSORS) + ["auto"], default="auto")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--count",    type=int,   default=0, help="0 = infinite")
    parser.add_argument("--baud",     type=int,   default=9600)
    parser.add_argument("--timeout",  type=float, default=3.0)
    args = parser.parse_args()

    print(f"\nProbing liquid level sensors on {args.port}...")

    if args.sensor == "auto":
        inst, sensor = None, None
        for key in SENSORS:
            inst, sensor = probe(args.port, key, args.baud, args.timeout)
            if inst:
                break
    else:
        inst, sensor = probe(args.port, args.sensor, args.baud, args.timeout)

    if inst is None:
        print("\nNo sensor found. Check port, wiring, and power.")
        sys.exit(1)

    read_loop(inst, sensor, args.count, args.interval)


if __name__ == "__main__":
    main()

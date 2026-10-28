"""Walk the data pins and print the status pins. No window needed.

Put an LED + 330R resistor (or a multimeter / scope) between a data pin
(2-9) and ground (18-25) to see each bit go high in turn.

    ./run.sh python pin_test.py               # uses $LPT_PORT
    ./run.sh python pin_test.py --psychopy    # go through psychopy.parallel
"""
import argparse
import time

from lpt import open_port


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="/dev/parportN or hex address like 0x378")
    ap.add_argument("--psychopy", action="store_true",
                    help="use psychopy.parallel.ParallelPort (ppdev only)")
    ap.add_argument("--dwell", type=float, default=0.5)
    args = ap.parse_args()

    if args.psychopy:
        import os
        from psychopy import parallel
        port = parallel.ParallelPort(
            address=args.port or os.environ.get("LPT_PORT", "/dev/parport0"))
        read_status = None
    else:
        port = open_port(args.port)
        read_status = port.readStatus

    try:
        for bit in range(8):
            port.setData(1 << bit)
            status = f"  status=0x{read_status():02X}" if read_status else ""
            print(f"D{bit} (pin {bit + 2}) high  data=0x{1 << bit:02X}{status}")
            time.sleep(args.dwell)
        port.setData(0xFF)
        print("all data pins high")
        time.sleep(args.dwell)
    finally:
        port.setData(0)
        print("all data pins low")
        if hasattr(port, "close"):
            port.close()


if __name__ == "__main__":
    main()

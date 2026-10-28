"""Minimal parallel-port access usable from inside the container.

Two backends:
  * ppdev  - /dev/parportN via the kernel ppdev driver (recommended; needs only
             the device node passed in, no privileged mode).
  * raw    - direct I/O-port writes via /dev/port at a base address such as
             0x378 (needs --cap-add SYS_RAWIO and --device /dev/port). Use this
             only if ppdev isn't available, e.g. a card the kernel won't bind.

Both expose the same API as psychopy.parallel.ParallelPort for the parts that
matter: setData, readData, readPin, setPin, plus status/control access.

Pin map (DB-25):
  data    D0-D7  -> pins 2-9      (output; input on bidirectional ports)
  status  S3-S7  -> pins 15,13,12,10,11 (input; pin 11 / BUSY is inverted)
  control C0-C3  -> pins 1,14,16,17 (output; 1,14,17 are inverted in hardware)
"""
import fcntl
import os
import struct

# ppdev ioctl numbers (linux/ppdev.h), x86/arm generic _IO encodings.
PPCLAIM = 0x0000708B
PPRELEASE = 0x0000708C
PPEXCL = 0x0000708F
PPRSTATUS = 0x80017081
PPRCONTROL = 0x80017083
PPWCONTROL = 0x40017084
PPRDATA = 0x80017085
PPWDATA = 0x40017086
PPDATADIR = 0x40047090

DATA_PINS = {2: 0, 3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 7}
STATUS_PINS = {15: 3, 13: 4, 12: 5, 10: 6, 11: 7}
CONTROL_PINS = {1: 0, 14: 1, 16: 2, 17: 3}


class _Base:
    def setPin(self, pin, high):
        if pin in DATA_PINS:
            bit, val = DATA_PINS[pin], self.readData()
            self.setData(val | (1 << bit) if high else val & ~(1 << bit))
        elif pin in CONTROL_PINS:
            bit, val = CONTROL_PINS[pin], self.readControl()
            self.setControl(val | (1 << bit) if high else val & ~(1 << bit))
        else:
            raise ValueError(f"pin {pin} is not an output pin")

    def readPin(self, pin):
        if pin in DATA_PINS:
            return (self.readData() >> DATA_PINS[pin]) & 1
        if pin in STATUS_PINS:
            return (self.readStatus() >> STATUS_PINS[pin]) & 1
        if pin in CONTROL_PINS:
            return (self.readControl() >> CONTROL_PINS[pin]) & 1
        raise ValueError(f"pin {pin} is not a signal pin")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


class PPDevPort(_Base):
    def __init__(self, device="/dev/parport0", exclusive=False):
        self.fd = os.open(device, os.O_RDWR)
        if exclusive:
            fcntl.ioctl(self.fd, PPEXCL)
        fcntl.ioctl(self.fd, PPCLAIM)

    def _rd(self, req):
        return struct.unpack("B", fcntl.ioctl(self.fd, req, b"\0"))[0]

    def _wr(self, req, value):
        fcntl.ioctl(self.fd, req, struct.pack("B", value & 0xFF))

    def setData(self, value):
        self._wr(PPWDATA, value)

    def readData(self):
        return self._rd(PPRDATA)

    def readStatus(self):
        return self._rd(PPRSTATUS)

    def readControl(self):
        return self._rd(PPRCONTROL)

    def setControl(self, value):
        self._wr(PPWCONTROL, value)

    def setDataDirection(self, input_mode):
        fcntl.ioctl(self.fd, PPDATADIR, struct.pack("i", 1 if input_mode else 0))

    def close(self):
        if self.fd is not None:
            fcntl.ioctl(self.fd, PPRELEASE)
            os.close(self.fd)
            self.fd = None


class RawPort(_Base):
    """I/O-port access through /dev/port: offset == port address."""

    def __init__(self, address=0x378):
        self.base = address
        self.fd = os.open("/dev/port", os.O_RDWR)

    def _rd(self, off):
        return os.pread(self.fd, 1, self.base + off)[0]

    def _wr(self, off, value):
        os.pwrite(self.fd, bytes([value & 0xFF]), self.base + off)

    def setData(self, value):
        self._wr(0, value)

    def readData(self):
        return self._rd(0)

    def readStatus(self):
        return self._rd(1)

    def readControl(self):
        return self._rd(2)

    def setControl(self, value):
        self._wr(2, value)

    def close(self):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None


def open_port(spec=None):
    """Open a port from a spec string: '/dev/parport0' or '0x378'.

    Defaults to $LPT_PORT, then /dev/parport0.
    """
    spec = spec or os.environ.get("LPT_PORT", "/dev/parport0")
    if spec.startswith("/dev/"):
        return PPDevPort(spec)
    return RawPort(int(spec, 0))

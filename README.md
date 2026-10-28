# psychopy-parport

PsychoPy in a Docker container with direct control of the host's parallel (LPT)
port pins, for sending trigger codes to EEG/MEG amplifiers, TMS units and similar.

```
 Linux host                                   container (psychopy-parport)
 ───────────                                  ────────────────────────────
 parallel port card ── parport_pc ── ppdev ──►  /dev/parport0 ──► lpt.py / psychopy.parallel
 X server (/tmp/.X11-unix) ────────────────────► PsychoPy window
 GPU (/dev/dri), sound (/dev/snd) ─────────────► OpenGL, audio
```

---

## 0. What you need

| Requirement | Why |
|---|---|
| **A Linux PC** (Ubuntu 22.04/24.04, Debian 12 or similar) | Docker on Windows/macOS runs containers inside a VM that can't reach LPT hardware. |
| **A real parallel port**: onboard, or a PCI/PCIe card | USB-to-parallel adapters are printer-only and **won't work** for triggers. |
| **An X11 desktop session** on that PC | PsychoPy draws its window through X11. Choose "Ubuntu on Xorg" at the login screen. |
| Docker Engine + the Compose plugin (v2.20+) | Installed in step 1. |

> On a Windows stimulus PC, skip Docker. Install PsychoPy natively; it drives
> the port through `inpoutx64.dll`.

---

## 1. Install Docker (once per machine)

```bash
# Ubuntu / Debian
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER        # run docker without sudo
sudo apt-get install -y x11-xserver-utils   # provides `xhost`, used by run.sh
```

**Log out and back in** for the group change to apply, then check:

```bash
docker run --rm hello-world
docker compose version               # should print v2.20 or newer
```

> Don't run `run.sh` with `sudo`. Under sudo the container can't open windows
> on your desktop. Use the `docker` group instead.

---

## 2. Copy this folder to the Linux PC

Any method works (USB stick, `scp`, `git clone`). Then:

```bash
cd psychopy-parport
chmod +x host-setup.sh run.sh
```

If you copied the files through Windows and get `bad interpreter: /bin/bash^M`,
convert the line endings: `sed -i 's/\r$//' *.sh`.

---

## 3. Set up the parallel port (once per machine)

```bash
./host-setup.sh
```

This script:
- loads the `parport_pc` and `ppdev` kernel drivers, now and at every boot;
- unloads and blacklists the `lp` printer driver, which otherwise holds the port;
- adds you to the `lp` group;
- prints what it found.

Expected output looks like:

```
== parallel ports ==
crw-rw---- 1 root lp 99, 0 Oct 28 10:12 /dev/parport0
parport0: base-addr 53264	53256  modes PCSPP,TRISTATE,COMPAT,EPP,ECP
  d010-d017 : parport0
```

- **`/dev/parport0` is listed** → use the default ppdev mode (step 4).
- **No `/dev/parport*` but the card is in `lspci`** → use raw mode (step 6),
  with the base address from `lspci -v` / `cat /proc/ioports`.

**Reboot** (or log out and in) once afterwards so the group change applies.

---

## 4. First run: check the pins

```bash
./run.sh
```

The first run builds the image, which takes **5–15 min** and downloads about
2 GB. Later runs start in seconds. The default command is `pin_test.py`, which
sets each data pin high in turn:

```
D0 (pin 2) high  data=0x01  status=0x7F
D1 (pin 3) high  data=0x02  status=0x7F
...
all data pins low
```

**Check it on the hardware:** connect an LED in series with a ~330 Ω resistor
(or a multimeter) between a data pin (2–9) and any ground pin (18–25). It should
light / read ~3.3–5 V when that bit is high. If your amplifier is already
connected, its trigger channel should show codes 1, 2, 4 … 128, then 255.

Options:

```bash
./run.sh python pin_test.py --dwell 2          # slower, easier to follow with a meter
./run.sh python pin_test.py --psychopy         # go through psychopy.parallel instead of lpt.py
LPT_PORT=/dev/parport1 ./run.sh                # a second port
```

---

## 5. Run an experiment

Put scripts in `experiments/`. That folder is mounted live at `/experiments`
in the container, so edits apply without a rebuild.

```bash
./run.sh python flip_trigger_demo.py           # demo: triggers locked to screen flips
./run.sh python my_experiment.py               # your own script
./run.sh bash                                  # interactive shell inside the container
```

Data files your script writes into `/experiments` (e.g. `data/` from
`ExperimentHandler`) end up in `experiments/` on the host.

### Sending triggers from your code

```python
from lpt import open_port          # picks up $LPT_PORT, which run.sh sets

port = open_port()
port.setData(0)

stim.draw()
win.callOnFlip(port.setData, 42)   # code goes out on the same flip the stimulus appears
win.flip()
core.wait(0.010)                   # pulse width: 10 ms is safe for most amplifiers
port.setData(0)                    # reset, or the next identical code won't register

port.close()
```

Or with PsychoPy's own API (ppdev mode only):

```python
from psychopy import parallel
port = parallel.ParallelPort(address='/dev/parport0')
port.setData(42)
```

`lpt.py` also has `setPin(pin, high)`, `readPin(pin)` (e.g. a button box on a
status pin), `readStatus()`, `setControl()` and `readControl()`, all using DB-25
pin numbers. The full pin map is in the docstring at the top of `lpt.py`.

### Experiments made in PsychoPy Builder

Compile the `.psyexp` to `.py` (Builder → *Compile to script*), save it in
`experiments/`, and run it with `./run.sh python my_task.py`. Builder's
**Parallel Port Out** component works if you set its address to
`/dev/parport0`. The Builder GUI itself isn't meant to run in this container.
Design on any machine and run the compiled script here.

---

## 6. Raw I/O mode (fallback for ports with no `/dev/parport0`)

Some PCIe cards (often ones with WCH CH382 or ASIX chips) don't get a
`/dev/parport*` device. Look up the base address:

```bash
lspci -v | grep -A6 -i parallel      # "I/O ports at d010" → base 0xd010
cat /proc/ioports | grep -i parport
```

Then pass it in:

```bash
RAW=1 LPT_PORT=0xd010 ./run.sh
RAW=1 LPT_PORT=0xd010 ./run.sh python my_experiment.py
```

With ECP cards, use the **first** I/O range; the second one is the ECP
registers. In this mode the container runs as root with `CAP_SYS_RAWIO`, which
lets it write **any** I/O port on the host, so keep it for dedicated lab PCs.
`psychopy.parallel` doesn't support this mode on Linux, so use `lpt.open_port()`.

---

## 7. Before collecting data: timing checklist

Running in a container adds no latency to the pin writes: they are the same
`ioctl` calls into the same host kernel. Screen timing still depends on the
host setup:

- [ ] **Check the GPU is in use:** `./run.sh glxinfo -B` should name your GPU,
      not `llvmpipe` (software rendering). For NVIDIA, see Troubleshooting.
- [ ] Turn off the desktop compositor or run fullscreen (`fullscr=True`), and
      enable vsync. Check `win.getActualFrameRate()` matches the monitor.
- [ ] Turn off screen blanking/power saving: `xset s off -dpms`.
- [ ] **Measure:** put a photodiode on the screen next to the trigger, record
      both on the amplifier, and check the onset delay and jitter across ~100 trials.
- [ ] Close other heavy programs. The container may raise its own priority
      (`core.rush(True)`) because it has `SYS_NICE` and `rtprio` in the compose file.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `/dev/parport0 not found` (from run.sh) | Run `./host-setup.sh`. Still missing → check `lspci` / `dmesg \| grep -i parport`. No device but the card is listed → use raw mode (step 6). |
| `OSError: [Errno 16] Device or resource busy` | Something else holds the port: the `lp` driver (`sudo rmmod lp`) or CUPS (`sudo systemctl stop cups`). |
| `Permission denied: '/dev/parport0'` | The host's group on the device doesn't match. Check `ls -l /dev/parport0`. run.sh reads the gid automatically, so make sure you started it through `./run.sh`, not plain `docker compose`. |
| `NoSuchDisplayException` / `cannot connect to X server` | Install `x11-xserver-utils` (for `xhost`), log in to an **X11** session, and launch from a terminal on the PC's desktop, not over SSH. Over SSH, `export DISPLAY=:0` first. |
| `error gathering device information ... /dev/snd` | The PC has no sound card. Delete the `/dev/snd` lines in `docker-compose.yml`. |
| `glxinfo -B` shows `llvmpipe` | No GPU access. Intel/AMD: check `/dev/dri` exists on the host. NVIDIA: install the NVIDIA Container Toolkit and add `gpus: all` under the services in `docker-compose.yml`. |
| Pins don't change in raw mode | Wrong base address. Try the other I/O range from `lspci -v`, and check `cat /proc/ioports`. |
| Amplifier sees the first code but not repeats | You aren't resetting to 0 between codes. Send `port.setData(0)` after each pulse. |
| `bad interpreter: /bin/bash^M` | Windows line endings: `sed -i 's/\r$//' *.sh`. |
| Build fails at the wxPython step | Temporary download failure from extras.wxpython.org. Rerun `./run.sh`; the steps that already finished are cached. |

Rebuild from scratch: `docker compose build --no-cache`.
Change the PsychoPy version: edit `PSYCHOPY_VERSION` in the `Dockerfile` and rerun.

---

## Files

| File | Purpose |
|---|---|
| `Dockerfile` | Ubuntu 22.04 + PsychoPy 2024.2.4 + wxPython + pyparallel |
| `docker-compose.yml` | `psychopy` (ppdev, default) and `psychopy-raw` (I/O ports) services |
| `lpt.py` | Pin-access library (ppdev or `/dev/port`), copied into the image |
| `host-setup.sh` | One-time host driver/permissions setup |
| `run.sh` | Launcher: works out gids, allows X11, picks the mode, runs the command |
| `experiments/pin_test.py` | Pin-walk test, no window |
| `experiments/flip_trigger_demo.py` | PsychoPy demo with triggers locked to screen flips |

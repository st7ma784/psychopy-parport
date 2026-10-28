#!/usr/bin/env bash
# One-time Linux host setup: load parport drivers, make them persistent,
# and report the port's address and device node.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    exec sudo "$0" "$@"
fi

modprobe parport_pc
modprobe ppdev
printf 'parport_pc\nppdev\n' > /etc/modules-load.d/parport.conf

# lp grabs the port for printing and blocks ppdev claims; keep it out.
if lsmod | grep -q '^lp '; then
    rmmod lp || true
fi
echo 'blacklist lp' > /etc/modprobe.d/no-lp.conf

echo "== parallel ports =="
ls -l /dev/parport* 2>/dev/null || echo "no /dev/parport* nodes - is there a port/card?"
for p in /proc/sys/dev/parport/parport*; do
    [[ -d $p ]] || continue
    echo "$(basename "$p"): base-addr $(cat "$p/base-addr")  modes $(cat "$p/modes")"
done
grep -i parport /proc/ioports || true

if [[ -n ${SUDO_USER:-} ]]; then
    usermod -aG lp "$SUDO_USER"
    echo "added $SUDO_USER to group lp (log out/in for it to apply on the host)"
fi

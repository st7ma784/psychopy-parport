#!/usr/bin/env bash
# Usage:
#   ./run.sh                                   # pin_test.py via ppdev
#   ./run.sh python flip_trigger_demo.py       # any command in /experiments
#   LPT_PORT=/dev/parport1 ./run.sh ...        # a different port
#   RAW=1 LPT_PORT=0xd010 ./run.sh ...         # raw I/O at a base address
set -euo pipefail
cd "$(dirname "$0")"

gid_of() { getent group "$1" | cut -d: -f3; }

if [[ -n ${RAW:-} ]]; then
    service=psychopy-raw
    export LPT_PORT=${LPT_PORT:-0x378}
else
    service=psychopy
    export LPT_PORT=${LPT_PORT:-/dev/parport0}
    if [[ ! -c $LPT_PORT ]]; then
        echo "$LPT_PORT not found - run ./host-setup.sh (or use RAW=1)" >&2
        exit 1
    fi
    export LP_GID=$(stat -c %g "$LPT_PORT")
fi

export VIDEO_GID=$(gid_of video || echo 44)
export AUDIO_GID=$(gid_of audio || echo 29)
export DISPLAY=${DISPLAY:-:0}

# Allow local containers to open windows on this X server.
xhost +local: >/dev/null 2>&1 || echo "warning: xhost failed; windows may not open" >&2

if [[ $# -eq 0 ]]; then
    set -- python pin_test.py
fi
exec docker compose run --rm --build "$service" "$@"

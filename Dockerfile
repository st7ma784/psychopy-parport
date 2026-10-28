# PsychoPy with Linux parallel-port (LPT) access.
# Must run on a *Linux* host with a real parallel port (PCI/PCIe card or onboard).
FROM ubuntu:22.04

ARG PSYCHOPY_VERSION=2025.2.4
# Newest prebuilt wheel on extras.wxpython.org for 22.04; newer PyPI releases are source-only.
ARG WXPYTHON_VERSION=4.2.2
ARG DEBIAN_FRONTEND=noninteractive

# System libs for pyglet/OpenGL, wxPython (GTK3), audio (PTB/portaudio), USB.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv python3-dev build-essential pkg-config \
        libgtk-3-0 libsdl2-2.0-0 libnotify4 libsm6 libxxf86vm1 libxtst6 libcurl4 libsecret-1-0 \
        libgl1 libglu1-mesa libegl1 libgl1-mesa-dri mesa-utils \
        libxcb-xinerama0 libxkbcommon-x11-0 \
        libasound2 libasound2-dev libpulse0 libpulse-dev \
        libportaudio2 portaudio19-dev libsndfile1 \
        libusb-1.0-0 libusb-1.0-0-dev \
        fonts-dejavu-core ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/psychopy
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# wxPython has no PyPI manylinux wheel; use the official Ubuntu 22.04 wheel
# so pip doesn't try (and fail) to compile it from source.
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
 && pip install --no-cache-dir \
        -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-22.04 \
        --only-binary wxPython "wxPython==${WXPYTHON_VERSION}" \
 && pip install --no-cache-dir "psychopy==${PSYCHOPY_VERSION}" pyparallel

# Non-root user; parport access comes from the host's `lp` gid via group_add.
RUN useradd -m -s /bin/bash experimenter
WORKDIR /experiments
COPY lpt.py /opt/lpt/lpt.py
ENV PYTHONPATH=/opt/lpt
# Bake in the bundled experiments so a pulled image runs on its own.
# run.sh still mounts ./experiments over this folder.
COPY --chown=experimenter experiments/ /experiments/

USER experimenter
CMD ["python", "/experiments/pin_test.py"]

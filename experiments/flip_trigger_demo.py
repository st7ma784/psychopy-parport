"""PsychoPy demo: send an EEG-style trigger code locked to the screen flip.

Each trial draws a stimulus and sends its code on the same flip via
win.callOnFlip, then resets the pins to 0 a few ms later.
Press Escape to quit.
"""
from psychopy import core, event, visual

from lpt import open_port

TRIGGER_MS = 0.010
CODES = {"left": 1, "right": 2}

port = open_port()
port.setData(0)
win = visual.Window(fullscr=False, size=(800, 600), color="grey", units="height")
stim = visual.Rect(win, width=0.2, height=0.2, fillColor="white")

try:
    for trial in range(20):
        side = "left" if trial % 2 == 0 else "right"
        stim.pos = (-0.25, 0) if side == "left" else (0.25, 0)
        stim.draw()
        win.callOnFlip(port.setData, CODES[side])
        win.flip()
        core.wait(TRIGGER_MS, hogCPUperiod=TRIGGER_MS)
        port.setData(0)

        core.wait(0.5)
        win.flip()
        core.wait(0.5)
        if event.getKeys(["escape"]):
            break
finally:
    port.setData(0)
    port.close()
    win.close()
    core.quit()

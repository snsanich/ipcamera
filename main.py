"""Script to gather IMDB keywords from 2013's top grossing movies."""
import sys
import os
import logging
import haffmpeg
import time
import queue
import threading

_LOGGER = logging.getLogger(__package__)

def _process_image(image):
    path = "{name}.jpg".format(name=time.time())
    """Callback for processing image."""
    
    _LOGGER.info("try it {path}".format(path=path))
    # Open file
    try:
        fd = os.open(path,os.O_RDWR|os.O_CREAT)    
        os.write(fd, image)
    finally:
        os.close(fd)

def read_image():
    
    command = [
        'C:\\ffmpeg-20170706-3b3501f-win32-static\\bin\\ffmpeg.exe',
        '-i',
        'rtsp://192.168.0.4:5540/out.h264',
        '-t', 
        '00:00:10',
        'output.mkv',
        '-y'
    ];

    is_running, proc = open(False, command)
    #time.sleep(30)
    close(is_running, proc, 100)

import subprocess

# pylint: disable=too-many-arguments,too-many-locals
def open(is_running, argv, stdout_pipe=False, stderr_pipe=True):
    """Start a ffmpeg instance and pipe output."""
    stdout = subprocess.PIPE if stdout_pipe else subprocess.DEVNULL
    stderr = subprocess.PIPE if stderr_pipe else subprocess.DEVNULL

    if is_running:
        _LOGGER.critical("FFmpeg is allready running!")
        return

    # start ffmpeg
    _LOGGER.debug("Start FFmpeg with %s", str(argv))
    try:
        return (True, subprocess.Popen(
            argv,
            stderr=stderr,
            stdout=stdout,
            stdin=subprocess.PIPE
        ))
    # pylint: disable=broad-except
    except Exception as err:
        _LOGGER.exception("FFmpeg fails %s", err)
        return (False, False)

def close(is_running, proc, timeout=5):
    """Stop a ffmpeg instance."""
    if not is_running:
        _LOGGER.error("FFmpeg isn't running!")
        return

    # set stop command for ffmpeg
    stop = b'q'

    try:
        # send stop to ffmpeg
        stdout, stderr = proc.communicate(timeout=timeout)
        _LOGGER.debug("Close FFmpeg process")
        _LOGGER.warning(stderr)
    except subprocess.TimeoutExpired:
        _LOGGER.warning("Timeout while waiting of FFmpeg")
        proc.kill()
        proc.wait()

def main():
    """Main entry point for the script."""
    """Return a still image response from the camera."""
    read_image()
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

"""Script to gather IMDB keywords from 2013's top grossing movies."""
import sys
import hass
import os
import asyncio
import logging

@asyncio.coroutine
async def read_image(core):
    
    from haffmpeg import ImageFrame, IMAGE_JPEG
    ffmpeg = ImageFrame('C:\\ffmpeg-20170706-3b3501f-win32-static\\bin\\ffmpeg.exe', loop=core.loop)

    image = await ffmpeg.get_image(
        'rtsp://192.168.0.4:5540/out.h264' # local camera
        #'rtsp://184.72.239.149/vod/mp4:BigBuckBunny_175k.mov' # video (started from beginning all the time)
        , output_format=IMAGE_JPEG,
        extra_cmd='-r 4 -vf "mpdecimate=hi=64*6:lo=64*5:frac=0.33,showinfo, setpts=\'N/(30*TB)\'" -preset slow -metadata title="xTitle" -vsync 2 -r 24')
    
    # Open file
    try:
        fd = os.open("f1.jpg",os.O_RDWR|os.O_CREAT)    
        os.write(fd, image)
    finally:
        os.close(fd)
    
    core.async_add_job(core.async_stop())

    return image

def main():
    """Main entry point for the script."""
    """Return a still image response from the camera."""

    core = hass.HomeAssistant()
    core.add_job(read_image, core)

    return core.start()
    pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    sys.exit(main())

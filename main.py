"""Script to gather IMDB keywords from 2013's top grossing movies."""
import sys
import hass
import os

def main():
    """Main entry point for the script."""
    """Return a still image response from the camera."""
    from haffmpeg import ImageFrame, IMAGE_JPEG

    core = hass.HomeAssistant()
    core.start()
    ffmpeg = ImageFrame('C:\ffmpeg-20170706-3b3501f-win32-static\bin\ffmpeg.exe', loop=core.loop)

    image = yield from ffmpeg.get_image(
        '', output_format=IMAGE_JPEG,
        extra_cmd='')
    os.write()
    return image
    pass

if __name__ == '__main__':
    sys.exit(main())
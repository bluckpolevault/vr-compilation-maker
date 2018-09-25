"""Extract thumbnails from movie"""
import shlex
import shutil
import subprocess
import sys

import constants as C
import util


def main():
    for movie_id, filename, metadata in util.get_file_data():
        dirname = util.get_folder(filename)
        screens = dirname.joinpath('screens')
        if screens.exists():
            continue
        screens_tmp = dirname.joinpath('screens-tmp')
        duration = metadata['video']['duration']
        orientation = metadata['format']['orientation']
        make_screens(movie_id, filename, duration, orientation, screens_tmp)
        shutil.move(str(screens_tmp), str(screens))


def make_screens(movie_id, filename, duration, orientation, screens_tmp):
    # Originally tried using the FPS filter, but I'm not really sure
    # where the first thumbnail starts and so that makes it hard to
    # match thumbnails with timestamps.  This way is slower, but I
    # have more control.
    screens_tmp.mkdir(exist_ok=False)
    rng = range(C.SCREENSHOT_START, int(duration), C.SCREENSHOT_FREQUENCY)
    video_filters = 'stereo3d={}l:ml'.format(orientation)
    db = util.get_db()
    cursor = db.cursor()
    for i, ts in enumerate(rng):
        thumbnail = screens_tmp.joinpath('thumb{:04d}.jpg'.format(i))
        cmd = 'ffmpeg -ss {} -i "{}" -vf "{}" -vframes 1 "{}"'.format(
            ts, filename, video_filters, thumbnail)
        print(cmd)
        subprocess.run(shlex.split(cmd), check=True)
        cursor.execute(
            'INSERT INTO thumbnail (movie_id, filename) VALUES (?, ?)',
            (movie_id, thumbnail.name))
    db.commit()


if __name__ == '__main__':
    sys.exit(main())

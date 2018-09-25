import argparse
import random
import os
import subprocess
import sys

import constants as C
import util


def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    all_screens = dict(get_all_screens())

    candidates = []
    keys = [(count_rated(v), k) for k, v in all_screens.items()]
    while keys and len(candidates) < 100:
        keys = sorted(keys)
        count, key = keys.pop(0)
        movie_screens = all_screens[key]
        try:
            thumbnail = pick_screen(movie_screens)
        except NoRemainingScreens:
            continue
        candidates.append(str(thumbnail))
    env = {k: v for k, v in os.environ.items()}
    env['PATH'] = str(C.SCRIPTSDIR) + ':' + env['PATH']
    cmd = ['qiv', '-CtS'] + candidates[:100]
    print(cmd)
    subprocess.run(cmd, env=env)


def count_rated(screens):
    return len([s for s in screens if s[1] is not None])


class NoRemainingScreens(Exception):
    pass


def pick_screen(movie_screens):
    positive_screens = [(i, s) for i, s in enumerate(movie_screens) if s[1] == 1]
    for i, s in positive_screens:
        if is_first_in_triple(i, movie_screens):
            continue
        if is_second_in_triple(i, movie_screens):
            continue
        if is_third_in_triple(i, movie_screens):
            continue
        if prev_is_not_rated(i, movie_screens):
            return movie_screens[i - 1][0]
        if next_is_not_rated(i, movie_screens):
            return movie_screens[i + 1][0]
    other_screens = [(i, s) for i, s in enumerate(movie_screens) if s[1] is None]
    if not other_screens:
        raise NoRemainingScreens()
    random.shuffle(other_screens)
    for i, screen in other_screens:
        if any_nearby_is_rated(i, movie_screens):
            continue
        return screen[0]
    return other_screens[0][1][0]


def any_nearby_is_rated(i, movie_screens):
    return (offset_is_rated(i, movie_screens, -2) or offset_is_rated(i, movie_screens, 1) or
            offset_is_rated(i, movie_screens, 1) or offset_is_rated(i, movie_screens, 2))


def is_first_in_triple(i, movie_screens):
    return (offset_is_rated(i, movie_screens, 1) and
            offset_is_rated(i, movie_screens, 2))


def is_second_in_triple(i, movie_screens):
    return (offset_is_rated(i, movie_screens, -1) and
            offset_is_rated(i, movie_screens, 1))


def is_third_in_triple(i, movie_screens):
    return (offset_is_rated(i, movie_screens, -2) and
            offset_is_rated(i, movie_screens, -1))


def prev_is_not_rated(i, movie_screens):
    return offset_is_not_rated(i, movie_screens, -1)


def next_is_not_rated(i, movie_screens):
    return offset_is_not_rated(i, movie_screens, 1)


def offset_is_rated(i, movie_screens, offset):
    idx = i + offset
    if idx < 0 or idx >= len(movie_screens):
        return False
    item = movie_screens[idx]
    return item[1] is not None


def offset_is_not_rated(i, movie_screens, offset):
    idx = i + offset
    if idx < 0 or idx >= len(movie_screens):
        return False
    item = movie_screens[idx]
    return item[1] is None


def get_all_screens():
    for _, filename, metadata in util.get_file_data():
        if not is_basic_format(metadata):
            continue
        base_dir = util.get_folder(filename)
        screens = base_dir.joinpath('screens')
        if not screens.exists():
            print('{} is missing screens!'.format(base_dir))
            continue
        yield base_dir, list(get_single_movie_screens(screens))


def is_basic_format(metadata):
    if metadata['format']['orientation'] != 'sbs':
        return False
    if metadata['format']['fov'] != '180':
        return False
    if metadata['format']['perspective'] != 'normal':
        return False
    return True


def get_single_movie_screens(screen_dir):
    base_dir = util.get_folder(screen_dir)
    db = util.get_db()
    cur = db.execute("""
select t.filename, t.rating
from thumbnail t
inner join movie m
on t.movie_id = m.id
where m.folder = ?""", (base_dir.name,))
    ratings = {row['filename']: row['rating'] for row in cur}
    for filename in sorted(screen_dir.iterdir()):
        if filename.suffix == '.jpg':
            yield filename, ratings.get(filename.name)


if __name__ == '__main__':
    sys.exit(main())

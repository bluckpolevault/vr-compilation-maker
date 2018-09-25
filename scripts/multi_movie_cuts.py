import argparse
import collections
import csv
import datetime
import os
import re
import random
import string
import subprocess
import sys

import constants as C
import review_screens as rs
import util


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resolution', default='1920x1080')
    parser.add_argument(
        '--duration', default=8*60, type=int, help="length of output compilation, in seconds")
    args = parser.parse_args()

    target_resolution = [int(p) for p in args.resolution.split('x')]

    used_cuts = get_used_cuts()
    filenames = []
    filemap = {}
    metadatas = {}

    # TODO: to really make this work, I'll need to remap from ab to sbs
    #       and to also make fisheye -> normal mapping
    #       and probably some sort of normalization to 180 dome. That seems hard, so instead
    #       we're going to skip the movies that aren't in the most common format (180, sbs, normal)
    for movie_id, filename, metadata in util.get_file_data():
        if not rs.is_basic_format(metadata):
            print('Skipping {} as its not in an easy format'.format(filename))
            continue
        filenames.append(filename)
        filemap[movie_id] = filename
        metadatas[movie_id] = metadata

    options = list(get_all_good_thumbs())
    random.shuffle(options)

    timestamps = list(get_timestamps(options, metadatas, used_cuts, args.duration))
    scale = "{w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2".format(
        w=int(target_resolution[0]), h=int(target_resolution[1]))

    filter_split = []
    filter_join = []
    vfilter_tmpl = "[{i}:v:0]trim={start}:{end},setpts=PTS-STARTPTS,scale={scale}[v{i}];"
    afilter_tmpl = "[{i}:a:0]atrim={start}:{end},asetpts=PTS-STARTPTS[a{i}];"
    inputs = []
    for i, item in enumerate(sorted(timestamps)):
        _, time_slice, movie_id = item
        movie_file = filemap[movie_id]
        inputs.append('-i')
        inputs.append(str(movie_file))
        start = time_slice[0]
        end = time_slice[1]
        filter_split.append(
            vfilter_tmpl.format(start=start, end=end, i=i, scale=scale))
        filter_split.append(
            afilter_tmpl.format(start=start, end=end, i=i))
        filter_join.append('[v{i}][a{i}]'.format(i=i))
    filter_complex = (
        ''.join(filter_split) +
        ''.join(filter_join) +
        'concat=n={}:v=1:a=1[outv][outa]'.format(len(timestamps)))
    print(filter_complex)
    now = datetime.datetime.now()
    output = 'collage/collage-{}-{}.mp4'.format(now.strftime('%Y%m%d%H%M'), random_string())
    cmd = ['ffmpeg'] + inputs + [
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-crf', '21', '-profile:v', 'baseline', '-level', '3.0',
        '-c:a', 'aac', '-b:a', '160k',
        output]
    print(cmd)
    subprocess.run(cmd)
    for item in sorted(timestamps):
        print(item[2])
    print(output)
    save_used_cuts(output, timestamps)


def get_used_cuts():
    """Return cuts that have been used in previous collages.

    Returns: mapping from movie to list of time slices.
    """
    results = collections.defaultdict(list)
    db = util.get_db()
    cur = db.execute('SELECT movie_id, start, end FROM used_cuts')
    for row in cur:
        time_slice = (float(row['start']), float(row['end']))
        results[row['movie_id']].append(time_slice)
    return results


def save_used_cuts(collage, timestamps):
    db = util.get_db()
    cur = db.cursor()
    for movie_id, time_slice, _ in timestamps:
        cur.execute('INSERT INTO used_cuts (collage, movie_id, start, end) VALUES (?, ?, ?, ?)',
                    (collage, movie_id, time_slice[0], time_slice[1]))
    db.commit()


def random_string(n=6):
    return ''.join([random.choice(string.ascii_lowercase) for _ in range(n)])


def get_all_good_thumbs(n=1):
    """Returns thumbnails that are rated positively AND are surrounded
    by positive ones.

    For example, if we have:
    0123
    ----
    -+++

    Then this would return only thumbnail 2.

    Its kind of weird if there are large gaps in what has been reviewed, but whatever

    Args:
        n: number of thumbs before and after that are needed. If,
           for example n=2 then 5 positive thumbnails in a row would be
           needed. (2 before, the middle one, 2 after)
    """
    thumbs_by_movie = collections.defaultdict(list)
    for row in get_all_thumbs():
        thumbs_by_movie[(row['id'], row['folder'])].append((row['filename'], row['rating']))
    for (movie_id, folder), thumbs in thumbs_by_movie.items():
        for good_thumb in bracketed_good_thumbs(thumbs, n):
            yield movie_id, C.RAWDIR.joinpath(folder, 'screens', good_thumb)


def get_all_thumbs():
    db = util.get_db()
    cur = db.execute("""
        select m.id, folder, t.filename, rating
        from thumbnail t
        inner join movie m
        on t.movie_id = m.id
    """)
    yield from cur


def bracketed_good_thumbs(thumbs, n=1):
    series_length = 2*n + 1
    thumbs = sorted(thumbs, key=lambda t: t[0])
    good_thumbs = []
    for thumb, rating in thumbs:
        if rating == 1:
            good_thumbs.append(thumb)
        else:
            good_thumbs = []
        if len(good_thumbs) >= series_length:
            yield good_thumbs[-(n + 1)]


def get_timestamps(thumbnails, metadatas, all_excludes, target_duration):
    """Yield clips from movies.

    Returns: list of (normalized_position, time_slice, movie_id) tuples

    Args:
        thumbnails: list of (movie_id, thumbnail paths)
        metadatas: mapping from movie_id -> metadata
        all_excludes: mapping from movie_id -> cuts to exclude
        target_duration: how long the resulting output should be, in seconds
    """
    used_movies = set()
    total_duration = 0
    for movie_id, thumb in thumbnails:
        assert thumb.parent.name == 'screens'
        # avoid having the same movie twice. Its more intersting and
        # its easier as I don't have to check for overlap
        if movie_id in used_movies:
            continue
        metadata = metadatas[movie_id]
        duration = metadata['video']['duration']
        ts = get_screen_timestamp(str(thumb))
        ts_slice = get_slice(ts)
        ts_slice = clip(ts_slice, 0, duration)
        excludes = all_excludes[movie_id]
        if has_overlap(ts_slice, excludes):
            continue
        used_movies.add(movie_id)
        # ts / duration gives the normalized position
        yield (ts / duration, ts_slice, movie_id)
        slice_duration = ts_slice[1] - ts_slice[0]
        total_duration += slice_duration
        if total_duration > target_duration:
            break


def has_overlap(candidate, existing):
    for slice_ in existing:
        for part in candidate:
            if slice_[0] <= part <= slice_[1]:
                return True
        if candidate[0] <= slice_[0] and slice_[1] <= candidate[1]:
            return True
    return False


def get_slice(base):
    a = C.SCREENSHOT_FREQUENCY - C.SCREENSHOT_FREQUENCY / 2
    b = C.SCREENSHOT_FREQUENCY + C.SCREENSHOT_FREQUENCY / 2
    ts = (base - random.uniform(a, b), base + random.uniform(a, b))
    return ts


def clip(arr, min_val, max_val):
    return [min(max_val, max(min_val, a)) for a in arr]


def get_screen_timestamp(screen):
    match = re.match('thumb(\d\d\d\d).jpg', os.path.basename(screen))
    return int(match.group(1)) * C.SCREENSHOT_FREQUENCY + C.SCREENSHOT_START


if __name__ == '__main__':
    sys.exit(main())

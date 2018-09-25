import json
import os
import pathlib
import sqlite3
import subprocess

import constants as C


valid_mov_ext = [
    ".avi", ".mpg", ".wmv", ".flv", ".mov", ".mp4",
    ".vob", ".divx", ".mkv", ".m4v", ".f4v", ".mpeg",
    ".webm",
]


def to_json(byts):
    return json.loads(byts.decode('utf-8'))


_db = None
def get_db() -> sqlite3.Connection:
    global _db
    if not _db:
        sqlite3.register_converter("JSON", to_json)
        db_path = C.DATADIR.joinpath('data.db')
        _db = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        _db.row_factory = sqlite3.Row
        c = _db.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS movie "
                  "(id INTEGER PRIMARY KEY, folder TEXT, filename TEXT, metadata JSON)")
        c.execute("CREATE TABLE IF NOT EXISTS thumbnail "
                  "(id INTEGER PRIMARY KEY, movie_id INTEGER, filename TEXT, rating INT,"
                  "FOREIGN KEY(movie_id) REFERENCES movie(id))")
        c.execute("CREATE TABLE IF NOT EXISTS used_cuts "
                  "(id INTEGER PRIMARY KEY, collage TEXT, movie_id INTEGER, start FLOAT, end FLOAT,"
                  "FOREIGN KEY(movie_id) REFERENCES movie(id))")
    return _db


def get_file_data():
    db = get_db()
    for row in db.execute('SELECT id, folder, filename, metadata FROM movie'):
        yield row['id'], C.RAWDIR.joinpath(row['folder'], row['filename']), row['metadata']


def is_movie_filename(filename):
    ext = os.path.splitext(filename)[1]
    return ext.lower() in valid_mov_ext


def get_duration(filename, codec_type='video'):
    cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,duration',
        '-print_format', 'json', filename
    ]
    output = json.loads(subprocess.check_output(cmd).decode('utf-8'))
    for stream in output['streams']:
        if stream['codec_type'] == codec_type:
            return float(stream['duration'])
    raise Exception('Unable to parse the video duration')


def get_folder(filename):
    parent = filename.parent
    while True:
        if parent.parent == C.RAWDIR:
            return parent
        parent = parent.parent
        if parent == pathlib.Path('/'):
            raise Exception('No valid folder found for {}'.format(filename))


def get_movie_id(filename):
    base_dir = get_folder(filename)
    db = get_db()
    cur = db.execute('SELECT id FROM movie WHERE folder = ?', (base_dir.name,))
    return cur.fetchone()['id']

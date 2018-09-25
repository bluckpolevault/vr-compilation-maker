import json
import os
import pathlib
import sys

import yaml

import constants as C
import metadata as mm
import util


def main():
    db = util.get_db()
    cur = db.cursor()
    for moviefile in get_movie_files():
        print(moviefile)
        base_dir = util.get_folder(moviefile)
        metadata = mm.get_override_metadata(base_dir)
        if 'video' not in metadata:
            metadata['video'] = mm.get_stats(moviefile)
        if 'format' not in metadata:
            metadata['format'] = mm.get_format(moviefile)
        if not mm.is_valid_format(metadata['format']):
            raise Exception(
                '{} does not a valid format: {}'.format(moviefile, metadata['format']))
        if mm.needs_actress(metadata):
            mm.populate_actress(moviefile, metadata)
        if mm.needs_studio(metadata):
            mm.populate_studio(moviefile, metadata)
        if mm.needs_title(metadata):
            mm.populate_title(moviefile, metadata)
        filename = moviefile.relative_to(base_dir)
        cur.execute('SELECT id FROM movie WHERE filename = ?', (str(filename),))
        # TODO: ensure only 0 or 1 response
        row = cur.fetchone()
        folder = base_dir.name
        if row:
            cur.execute(
                'UPDATE movie SET folder = ?, metadata = ? WHERE id=?',
                (folder, json.dumps(metadata), row['id']))
        else:
            # don't need to save the file data as that is in a column by itself
            metadata.pop('file', None)
            cur.execute(
                'INSERT INTO movie (folder, filename, metadata) VALUES (?, ?, ?)',
                (folder, str(filename), json.dumps(metadata)))
    db.commit()


def get_movie_files():
    for dirpath in C.RAWDIR.iterdir():
        if not dirpath.is_dir():
            continue
        mf = get_movie_file(dirpath)
        if not mf:
            raise Exception('No movie in {}'.format(dirpath))
        yield mf


def get_movie_file(dirpath):
    metadata = mm.get_override_metadata(dirpath)
    if 'file' in metadata:
        path = pathlib.Path(metadata['file'])
        if path.is_absolute():
            print('*** fixing absolute path ***')
            metadata['file'] = str(path.relative_to(dirpath))
            mm.save_override_metadata(dirpath, metadata)
            return path.resolve()
        return dirpath.joinpath(path).resolve()
    movie_filenames = list(get_all_movie_files(dirpath))
    if len(movie_filenames) == 0:
        raise Exception('{} does not have a movie'.format(dirpath))
    if len(movie_filenames) > 1:
        raise Exception('{} has {} movies'.format(dirpath, len(movie_filenames)))
    return movie_filenames[0]


def get_all_movie_files(dirpath):
    for dirpath, dirnames, filenames in os.walk(str(dirpath)):
        for fn in filenames:
            if not util.is_movie_filename(fn):
                continue
            if fn.startswith('collage'):
                continue
            if fn.startswith('output'):
                continue
            yield pathlib.Path(dirpath).joinpath(fn)


if __name__ == '__main__':
    sys.exit(main())

import json
import os
import pathlib
import re
import shlex
import subprocess

import yaml

import constants as C
import util


def get_override_metadata(dirpath):
    metadata_file = dirpath.joinpath('metadata.yaml')
    if metadata_file.exists():
        with metadata_file.open() as fin:
            metadata = yaml.safe_load(fin.read())
            apply_corrections(dirpath, metadata)
            return metadata
    return {}


def apply_corrections(dirpath, metadata):
    need_save = False
    if 'format' in metadata:
        if not isinstance(metadata['format']['fov'], str):
            metadata['format']['fov'] = str(metadata['format']['fov'])
            need_save = True
    if 'file' in metadata:
        if not isinstance(metadata['file'], str):
            metadata['file'] = str(metadata['file'])
            need_save = True
    if need_save:
        save_override_metadata(dirpath, metadata)



def save_override_metadata(dirpath, metadata):
    metadata_file = dirpath.joinpath('metadata.yaml')
    with metadata_file.open('w') as fout:
        yaml.safe_dump(metadata, fout, default_flow_style=False)


def get_row(filename):
    stats = get_stats(filename)
    fmt = get_format(filename)
    if not is_valid_format(fmt):
        raise Exception('{} does not a valid format: {}'.format(filename, fmt))
    return {
        'FILENAME': filename,
        'DURATION': stats['duration'],
        'WIDTH': stats['width'],
        'HEIGHT': stats['height'],
        'FOV': fmt[0],
        'ORIENTATION': fmt[1],
        'PERSPECTIVE': fmt[2],
    }


def is_valid_format(fmt):
    return (
        fmt['fov'] in ('180', '220', '360') and
        fmt['orientation'] in ('sbs', 'ab') and
        fmt['perspective'] in ('normal', 'fisheye'))


def get_format(fn):
    base_dir = util.get_folder(fn)
    format_file = base_dir.joinpath('format')
    if format_file.exists():
        print('*** moving format to metadata ***')
        fov, orient, persp = tuple(format_file.open().read().strip().split(','))
        fmt = {'fov': fov, 'orientation': orient, 'perspective': persp}
        if not is_valid_format(fmt):
            raise Exception('{} does not a valid format: {}'.format(fn, fmt))
        metadata = get_override_metadata(base_dir)
        metadata['format'] = fmt
        save_override_metadata(base_dir, metadata)
        return fmt
    if re.search('180x180_3dh', str(fn)):
        return {'fov': '180', 'orientation': 'sbs', 'perspective': 'normal'}
    raise Exception('For {}, the format is unknown'.format(fn))


def get_stats(filename):
    keys = ['duration', 'height', 'width']
    fns = [float, int, int]
    stats = run_ffprobe(filename, keys)
    return {k:fn(stats[k]) for k,fn in zip(keys, fns)}


def run_ffprobe(fn, entries):
    entry_str = ','.join(entries)
    p = subprocess.run(
            shlex.split('ffprobe -show_entries stream=codec_type,{} -print_format json "{}"'.format(entry_str, fn)),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out = json.loads(p.stdout.decode('utf-8'))
    except json.decoder.JSONDecodeError:
        print(p.stdout.decode('utf-8'))
        print(p.stderr)
        raise
    video = next(s for s in out['streams'] if s['codec_type'] == 'video')
    return video


def needs_actress(existing_metadata):
    return not ('actress' in existing_metadata or 'actresses' in existing_metadata)


def populate_actress(filename, existing_metadata):
    actresses = list(get_actresses(filename))
    if len(actresses) == 1:
        existing_metadata['actress'] = actresses[0]
    else:
        existing_metadata['actresses'] = actresses


def get_actresses(filename):
    directory = util.get_folder(filename)
    parts = directory.name.split('-')
    actresses = parts[:-1]
    for actress in actresses:
        yield ' '.join(p.capitalize() for p in actress.split('.'))


def needs_studio(existing_metadata):
    return 'studio' not in existing_metadata


def populate_studio(filename, existing_metadata):
    studio = get_studio(filename)
    if not studio:
        # TODO: ask user for studio
        print('{} is missing a studio'.format(filename))
    else:
        existing_metadata['studio'] = studio


def get_studio(filename):
    # the studio is usually in the filename so search there first and
    # then, if the torrent also included a folder, check that for the
    # studio information as well
    bases = list(_get_bases(filename))
    for base in bases:
        studio = _get_studio_from_base(base)
        if studio:
            return studio


def _get_bases(filename):
    while filename != C.RAWDIR:
        yield filename.name
        filename = filename.parent
    

def _get_studio_from_base(base):
    base = re.sub('[^a-z]', '', base.lower())
    searches = [
        ('vrhush', 'VRHush'),
        ('wankzvr', 'WankzVR'),
        ('vrbangers', 'VR Bangers'),
        ('virtualrealporn', 'Virtual Real Porn'),
        ('^nam', 'Naughty America'),
        ('naughtyamerica', 'Naughty America'),
        ('badoinkvr', 'BaDoink VR'),
        ('vrpfilms', 'VRP Films'),
        ('tmwvrnet', 'TMW VR Net'),
        ('sexbabesvr', 'Sex Babes VR'),
        ('hologirlsvr', 'HoloGirlsVR'),
        ('virtualtaboo', 'Virtual Taboo'),
    ]
    for pattern, studio in searches:
        if re.search(pattern, base):
            return studio


def needs_title(existing_metadata):
    return 'title' not in existing_metadata


def populate_title(filename, existing_metadata):
    title = get_title(filename)
    existing_metadata['title'] = title


def get_title(filename):
    directory = util.get_folder(filename)
    parts = directory.name.split('-')
    return ' '.join(p.capitalize() for p in parts[-1].split('.'))


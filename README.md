# VR Compilation Maker

This is a very hacky and manual way of creating VR compilations. It
also is a very, very basic organizational tool.

I wrote it for me; its probably a pain for other people to use, but
maybe there is something re-usable or interesting.

## Required Software

* ffmpeg
  * with libx264 enabled
  * also uses the default, native AAC encoder for audio (https://trac.ffmpeg.org/wiki/Encode/AAC#NativeFFmpegAACEncoder)
* qiv
  * https://spiegl.de/qiv/
* python3

This probably only works on linux. It could work on OSX, but I don't
think `qiv` works on OSX so you'd need to find a different way to rate
the thumnails.

## Installation

So, this is super hacky, but quite simple. Usually you can just
install a python package using `pip install <package>`. But, this
depends on a certain folder structure and so installation just
involves cloning and installing one dependency:

```
git clone https://github.com/bluckpolevault/vr-compilation-maker.git VR
python3 -m pip install --user pyyaml
```

I also set the PYTHONPATH variable
```
export PYTHONPATH=$PWD/VR/scripts
```

## Workflow and Scripts

When I get a new VR video, I create a new folder in the `VR/raw`
directory with the format `<actress.name>-<movie.title>` and if there
is more than one actress, the format will be
`<actress.name>-<other.actress>-<another.actress>-<movie-title>` and
then inside that folder I'll move the video.

Sometimes I'll also create a file names `metadata.yaml` that contains
the metadata for the video. I'll document that later but frequently
most of the metadata can be parsed from the folder name and file
name. The yaml file is a way of providing metadata that can't be
parsed or as an override.

Then, I'll run the `scripts/save_metadata.py` script. This populates
an sqlite database with metadata - combining the parsed data with the
overrides and saving it for easy access.

Next, `scripts/make_thumbs.py`. This creates screens/thumbnails every
15 seconds.

After that, running `scripts/review_screens.py` will launch qiv. qiv
has a cool feature that if you press one of the number keys (0-9) it
will call the `qiv-command` script with the image filename and the key
pressed. Only the 0 and 1 keys work and I am using 0 to mean
disliked/thumbsdown and 1 to mean liked/thumbsup.

After reviewing some screens, I'll have enough data to run
`scripts/multi_movie_cuts.py`. This script takes the liked screens and
makes roughly 30 second cuts of the movie around those screens, joins
them together and makes a new compilation. The output will be saved in
the `VR/collage` folder.

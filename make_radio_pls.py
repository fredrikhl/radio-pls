#!/usr/bin/env python
# encoding: utf-8
""" Make radio PLS playlists. """
from __future__ import unicode_literals, print_function

import argparse
import os
import signal
import sys

# compat
if sys.version_info.major < 3:
    str = unicode


_playlist_format = """
[playlist]

{content}

NumberOfEntries={entries:d}
Version={version:d}
""".strip()


_entry_format = """
Title{num:d}={title}
File{num:d}={url}
Length{num:d}={length:d}
""".strip()


def format_playlist(entries):
    """ Format a PLS playlist from a list of formatted track entries. """
    return _playlist_format.format(
        content="\n\n".join(
            "{:{index}}".format(entry, index=idx)
            for idx, entry in enumerate(entries, 1)
        ),
        entries=len(entries),
        version=2)


def format_entry(title, url, length=-1, num=0):
    """ Format a single playlist track. """
    return _entry_format.format(title=title, url=url, length=length, num=num)


class PlsEntry(object):
    """ A playlist entry. """

    __slots__ = ('title', 'file', 'length', 'tags')

    def __init__(self, title, fileurl, length=-1, tags=None):
        """ Create a playlist entry.

        :param str title: Title of the playlist entry.
        :param str fileurl: The path or url of the playlist entry.
        :param int length: The playtime length of the playlist item
        """
        self.title = str(title)
        self.file = str(fileurl)
        self.length = int(length)
        self.tags = set(tags or ())

    def __cmp__(self, other):
        """ Compare playlist entries by title. """
        if isinstance(other, PlsEntry):
            return cmp(self.title, other.title)
        return cmp(str(self), str(other))

    def __str__(self):
        """ String value of this playlist entry. """
        return str(self.title)

    def __repr__(self):
        """ Literal representation of this entry. """
        u = '{cls}({t}, {f}, length={l}, tags={tt})'.format(
            cls=type(self).__name__,
            t=repr(self.title),
            f=repr(self.file),
            l=repr(self.length),
            tt=repr(tuple(self.tags)),
        )
        return str(u)

    def __format__(self, entry_number):
        num = int(entry_number)
        return format_entry(self.title, self.file, length=self.length, num=num)

    def has_tag(self, tag):
        return tag in self.tags

    @classmethod
    def from_dict(cls, d):
        return cls(d['name'], d['url'], tags=d.get('tags'))


class PlaylistCollection(object):
    """ A collection of PlsEntries. """

    def __init__(self, *args):
        self.__entries = []

        for item in args:
            if not isinstance(item, PlsEntry):
                raise ValueError("Invalid item {!r}".format(item))
            self.add(item)

    @property
    def entries(self):
        return self.__entries

    def add(self, item):
        if not isinstance(item, PlsEntry):
            raise ValueError("Invalid item {!r}".format(item))
        elif item in self.entries:
            return
        self.__entries.append(item)

    def get(self, *tags):
        for item in self.entries:
            if not tags:
                yield item
            elif any(item.has_tag(tag) for tag in tags):
                yield item

    @classmethod
    def from_data(cls, data):
        entries = tuple(PlsEntry.from_dict(i) for i in data)
        return cls(*entries)


def parse_config(filename):

    def parse_json_config(filename):
        import json
        data = {}
        with open(filename, 'r') as f:
            data = json.load(f)
        return data

    def parse_yaml_config(filename):
        import yaml
        data = {}
        with open(filename, 'r') as f:
            data = yaml.safe_load(f)
        return data

    f_ext = os.path.splitext(filename)[1]
    if f_ext in ('.yml', '.yaml'):
        return parse_yaml_config(filename)
    elif f_ext in ('.json', '.js'):
        return parse_json_config(filename)
    raise argparse.ArgumentTypeError(
        "Unknown file type '{!s}' ({!s})".format(f_ext, filename))


default_encoding = 'utf-8'
default_config = os.path.join(os.path.dirname(__file__), 'streams.yml')

parser = argparse.ArgumentParser(
    description="Create a playlist (pls) with a selection of streams",
)
parser.add_argument(
    '-c', '--config',
    type=str,
    default=default_config,
    help="read streams from %(metavar)s (%(default)s)",
    metavar='<file>',
)
parser.add_argument(
    '-l', '--list',
    action='store_true',
    default=False,
    help="list channels and exit",
)
parser.add_argument(
    '-t', '--list-tags',
    action='store_true',
    default=False,
    help="list available tags and exit",
)
parser.add_argument(
    'tags',
    nargs='*',
    help="only include streams with one of the given tags",
)


def _get_collection(config=None):
    if config:
        return PlaylistCollection.from_data(parse_config(config))
    else:
        return PlaylistCollection()


def main(args=None):
    args = parser.parse_args()

    pls_data = _get_collection(args.config)
    entries = pls_data.get(*(args.tags or ()))

    if args.list:
        for entry in entries:
            print("{!s} ({!s})".format(entry, ','.join(entry.tags)))
        raise SystemExit(0)

    if args.list_tags:
        tags = dict()
        for entry in entries:
            for tag in entry.tags:
                tags.setdefault(tag, []).append(entry)
        for tag in sorted(tags):
            print(
                "{!s}:\n  {!s}".format(
                    tag, "\n  ".join(str(e) for e in tags[tag])))
        raise SystemExit(0)

    print(format_playlist(list(entries)))


def get_safe_print(encoding):

    _real_print = print

    def encode_print(*args, **kwargs):
        kwargs.setdefault('file', sys.stdout)
        if kwargs['file'] == sys.stdout:
            args = tuple(
                value.encode(encoding)
                if isinstance(value, str)
                else value
                for value in args)
        _real_print(*args, **kwargs)
        return encode_print


if __name__ == '__main__':
    # Kill silently if stdin, stdout, stderr is closed
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    if (not os.isatty(sys.stdout.fileno()) and
            'PYTHONIOENCODING' not in os.environ):
        # Stdout is redirected, and we're missing a sensible default encoding.
        # Try to encode all unicode objects as DEFAULT_ENCODING when printing
        # to stdout.
        print = get_safe_print(default_encoding)
    main()

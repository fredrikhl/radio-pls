#!/usr/bin/env python
# encoding: utf-8
""" Make radio PLS playlists. """

from __future__ import unicode_literals, print_function

import argparse
import os
import signal
import sys

PLAYLIST_FORMAT = """
[playlist]

{content!s}

NumberOfEntries={entries:d}
Version={version:d}
""".strip()

ENTRY_FORMAT = """
Title{num:d}={title!s}
File{num:d}={url!s}
Length{num:d}={length:d}
""".strip()

DEFAULT_ENCODING = 'utf-8'

DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              'radio.pls.yml')


def format_playlist(entries):
    """ Format a PLS playlist from a list of formatted track entries. """
    return PLAYLIST_FORMAT.format(
        content="\n\n".join(
            ["{:{index}}".format(entry, index=idx+1)
             for idx, entry in enumerate(entries)]),
        entries=len(entries),
        version=2)


def format_entry(title, url, length=-1, num=0):
    """ Format a PLS playlist track entry. """
    return ENTRY_FORMAT.format(
        title=title, url=url, length=length, num=num)


class PlsEntry(object):
    """ A playlist entry. """

    __slots__ = ['title', 'file', 'length', 'tags']

    def __init__(self, title, fileurl, length=-1, tags=None):
        """ Create a playlist entry.

        :param str title:
            Title of the playlist entry.

        :param str fileurl:
            The path or url of the playlist entry.

        :param int length:
            The playtime length of the playlist item (-1 is infinite, this is
            the default).
        """
        self.title = unicode(title)
        self.file = unicode(fileurl)
        self.length = int(length)
        self.tags = set()
        for tag in (tags or []):
            self.add_tag(tag)

    @staticmethod
    def make_entry(title, url, length, num):
        """ Make a PLS playlist entry. """
        return "\n".join([
            "Title{:d}={!s}".format(num, title),
            "File{:d}={!s}".format(num, url),
            "Length{:d}={!s}".format(num, length), ])

    def __cmp__(self, other):
        """ Compare playlist entries by title. """
        if isinstance(other, PlsEntry):
            return cmp(self.title, other.title)
        return cmp(unicode(self), unicode(other))

    def __str__(self):
        """ String value of this playlist entry. """
        return str(self.title)

    def __unicode__(self):
        """ Unicode value of this playlist entry. """
        return self.title

    def __repr__(self):
        """ Literal representation of this entry. """
        u = '{!s}({!r}, {!r}, length={!r}, tags={!r})'.format(
            type(self).__name__,
            self.title, self.file, self.length, list(self.tags))
        return str(u)

    def __format__(self, entry_number):
        num = int(entry_number)
        return format_entry(self.title, self.file, length=self.length, num=num)

    def str(self, num):
        """ Create a playlist entry string for this entry. """
        return "{:{num:d}}".format(self, num=num)

    def add_tag(self, tag):
        self.tags.add(tag)

    def has_tag(self, tag):
        return tag in self.tags

    @classmethod
    def from_dict(cls, dict_):
        entry = cls(dict_['name'], dict_['url'])
        for tag in dict_.get('tags', []):
            entry.add_tag(tag)
        return entry


class PlaylistCollection(object):
    """ A collection of PlsEntries. """

    def __init__(self, *args):
        self.__entries = list()

        for item in args:
            if not isinstance(item, PlsEntry):
                raise ValueError("Invalid item {!r}".format(item))
            self.add(item)

    @staticmethod
    def make_pls(pls_list):
        return format_playlist(pls_list)

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
        entries = [PlsEntry.from_dict(i) for i in data]
        return cls(*entries)


def add_bbc(collection):
    """ hack, the bbc url seems to need an updated timestamp. """

    def __make_bbc_url(name):
        from time import time
        return 'http://bbcmedia.ic.llnwd.net/stream/{:s}'.format(
            'bbcmedia_{:s}_mf_p?s={:d}'.format(name, int(time())))

    entries = [
        PlsEntry('BBC Radio 1', __make_bbc_url('radio1')),
        PlsEntry('BBC Radio 2', __make_bbc_url('radio2')),
        PlsEntry('BBC Radio 3 Classical', __make_bbc_url('radio3')),
        PlsEntry('BBC Radio 4', __make_bbc_url('radio4fm')),
        PlsEntry('BBC Radio 5 Live', __make_bbc_url('radio5live')),
        PlsEntry('BBC Radio 6 Music', __make_bbc_url('6music')),
    ]

    for entry in entries:
        entry.add_tag('bbc')
        collection.add(entry)


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
            data = yaml.load(f)
        return data

    f_ext = os.path.splitext(filename)[1]
    if f_ext in ('.yml', '.yaml'):
        return parse_yaml_config(filename)
    elif f_ext in ('.json', '.js'):
        return parse_json_config(filename)
    raise argparse.ArgumentTypeError(
        "Unknown file type '{!s}' ({!s})".format(f_ext, filename))


def main(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=False,
                        help="List channels")
    parser.add_argument('-c', '--config',
                        type=str,
                        default=DEFAULT_CONFIG,
                        help="Use config %(metavar)s (%(default)s).")
    parser.add_argument('-t', '--list-tags',
                        action='store_true',
                        default=False,
                        help="List tags")
    parser.add_argument('tags',
                        default=[],
                        nargs='*',
                        help="Only include tags.")

    args = parser.parse_args()

    if args.config:
        custom = PlaylistCollection.from_data(parse_config(args.config))
    else:
        custom = PlaylistCollection()

    add_bbc(custom)

    entries = custom.get(*(args.tags))

    if args.list:
        for entry in entries:
            print("{!s} ({!s})".format(entry, ','.join(entry.tags)))
    elif args.list_tags:
        tags = dict()
        for entry in entries:
            for tag in entry.tags:
                tags.setdefault(tag, []).append(entry)
        for tag in sorted(tags):
            print(
                "{!s}:\n  {!s}".format(
                    tag, "\n  ".join(unicode(e) for e in tags[tag])))
    else:
        print(format_playlist(list(entries)))


if __name__ == '__main__':
    # Kill silently if stdin, stdout, stderr is closed
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    if (not os.isatty(sys.stdout.fileno()) and
            'PYTHONIOENCODING' not in os.environ):
        # Stdout is redirected, and we're missing a sensible default encoding.
        # Try to encode all unicode objects as DEFAULT_ENCODING when printing
        # to stdout.
        real_print = print

        def print(*args, **kwargs):
            kwargs.setdefault('file', sys.stdout)
            if kwargs['file'] == sys.stdout:
                args = list(args)
                for index, value in enumerate(args):
                    if isinstance(value, unicode):
                        args[index] = value.encode(DEFAULT_ENCODING)
            real_print(*args, **kwargs)

    main()

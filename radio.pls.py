#!/usr/bin/env python
# encoding: utf-8
""" Make radio PLS playlists. """

from __future__ import unicode_literals, print_function

import os
from collections import OrderedDict

PLAYLIST_FORMAT = """[playlist]

{content!s}

NumberOfEntries={entries:d}
Version={version:d}"""


class PlsEntry(object):
    """ A playlist entry. """

    __slots__ = ['title', 'file', 'length']

    def __init__(self, title, fileurl, length=-1):
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
        u = '{!s}({!r}, {!r}, length={!r})'.format(
            type(self).__name__, self.title, self.file, self.length)
        return str(u)

    def str(self, num):
        """ Create a playlist entry string for this entry. """
        return self.make_entry(self.title, self.file, self.length, num)


class PlsPlaylist(object):
    """ A collection of PlsEntries. """

    def __init__(self, title, **kwargs):
        self.__title = unicode(title)
        self.__entries = OrderedDict()

        for name in sorted(kwargs.keys()):
            if not isinstance(kwargs[name], (PlsEntry, PlsPlaylist)):
                continue
            self.add(name, kwargs[name])

    @property
    def entries(self):
        """ All entries in this playlist. """
        for item in self.__entries.itervalues():
            if isinstance(item, PlsPlaylist):
                for subitem in item.entries:
                    yield subitem
            elif isinstance(item, PlsEntry):
                yield item

    @property
    def names(self):
        """ All entry titles in this playlist. """
        for name, item in self.__entries.iteritems():
            if isinstance(item, PlsPlaylist):
                for subname in item.names():
                    yield '{}.{}'.format(name, subname)
            elif isinstance(item, PlsEntry):
                yield name

    def new(self, name, title, fileurl, length=-1):
        """ Create a new entry in this playlist. """
        item = PlsEntry(title, fileurl, length)
        self.add(name, item)

    def add(self, name, item):
        """ Add an entry in this playlist. """
        if '.' in name:
            return
        if name in self.__entries:
            del self.__entries[name]
        elif item in self.__entries.values():
            for k, v in self.__entries.iteritems():
                del self.__entries[k]
                break
        self.__entries[name] = item

    def get(self, name):
        """ Get an entry by title from this playlist. """
        rest = None
        if '.' in name:
            name, rest = name.split('.', 1)
        item = self.__entries[name]
        if rest is not None and isinstance(item, PlsPlaylist):
            return item.get(rest)
        return item

    @staticmethod
    def make_pls(pls_list):
        return PLAYLIST_FORMAT.format(
            content="\n\n".join(
                [entry.str(idx + 1) for idx, entry in enumerate(pls_list)]),
            entries=len(pls_list),
            version=2)

    def pls(self):
        """ Make a PLS string from the PlsEntries in this class. """
        return self.make_pls(list(self.entries))

    def str(self, indent='  ', num=0):
        lines = []
        for name, item in self.__entries.iteritems():
            if isinstance(item, PlsPlaylist):
                lines.append(
                    "{}{}: {}\n{}".format(
                        indent * num,
                        name,
                        item,
                        item.str(indent=indent, num=num+1)))
            elif isinstance(item, PlsEntry):
                lines.append(
                    '{}{}: {}'.format(indent * num, name, item))
        return "\n".join(lines)

    def __str__(self):
        return str(unicode(self))

    def __unicode__(self):
        return '{!s} [{}]'.format(self.__title, ', '.join(self.names))

    def __repr__(self):
        u = '{!s}({!r}, {!s})'.format(
            type(self).__name__,
            self.__title,
            ', '.join('{}={}'.format(k, repr(v)) for k, v
                      in self.__entries.iteritems()))
        return str(u)


class PlaylistCollection(object):
    """ A collection of PlsEntries. """

    def __init__(self, symbol, **kwargs):
        self.__symbol = symbol
        self.__entries = OrderedDict()

        for attr in sorted(vars(type(self)).keys()):
            if not isinstance(getattr(self, attr), PlsEntry):
                continue
            self.add(attr, getattr(self, attr))
            delattr(type(self), attr)

        for name in sorted(kwargs.keys()):
            if not isinstance(kwargs[name], PlsEntry):
                continue
            self.add(name, kwargs[name])

    @staticmethod
    def make_pls(pls_list):
        return PLAYLIST_FORMAT.format(
            content="\n\n".join(
                [entry.str(idx + 1) for idx, entry in enumerate(pls_list)]),
            entries=len(pls_list),
            version=2)

    @property
    def entries(self):
        return self.__entries.values()

    @property
    def names(self):
        return self.__entries.keys()

    @property
    def symbol(self):
        return self.__symbol or ''

    @property
    def name(self):
        try:
            name = self.__doc__.strip()
            if name:
                return name
        except AttributeError:
            pass
        return type(self).__name__

    def __key_of(self, item):
        for k, v in self.__entries.iteritems():
            if v == item:
                return k
        return None

    def add(self, symbol, item):
        if self.symbol:
            symbol = '{!s}_{!s}'.format(self.symbol, symbol)
        if symbol in self.names:
            del self.__entries[symbol]
        elif item in self.entries:
            k = self.__key_of(item)
            del self.__entries[k]
        self.__entries[symbol] = item

    def get(self, symbol):
        try:
            return self.__entries[symbol]
        except KeyError:
            if self.symbol:
                return self.__entries['{!s}_{!s}'.format(self.symbol, symbol)]
            raise

    def pls(self):
        """ Make a PLS string from the PlsEntries in this class. """
        return self.make_pls(self.entries)


class NrkRadio(PlaylistCollection):
    """ NRK Radio """

    p1 = PlsEntry(
        'NRK P1, Østlandssendingen',
        'http://lyd.nrk.no/nrk_radio_p1_ostlandssendingen_mp3_h')

    p2 = PlsEntry(
        'NRK P2',
        'http://lyd.nrk.no/nrk_radio_p2_mp3_h')

    p3 = PlsEntry(
        'NRK P3',
        'http://lyd.nrk.no/nrk_radio_p3_mp3_h')

    rr = PlsEntry(
        'NRK Radioresepsjonen',
        'http://lyd.nrk.no/nrk_radio_p3_radioresepsjonen_mp3_h')

    p3_pyro = PlsEntry(
        'NRK P3 Pyro',
        'http://lyd.nrk.no/nrk_radio_p3_pyro_mp3_h')

    p3_urort = PlsEntry(
        'NRK P3 Urørt',
        'http://lyd.nrk.no/nrk_radio_p3_urort_mp3_h'),

    news = PlsEntry(
        'NRK Alltid Nyheter',
        'http://lyd.nrk.no/nrk_radio_alltid_nyheter_mp3_h')


class UniRadio(PlaylistCollection):
    """ College Radio """

    kalx = PlsEntry(
        'KALX 90.7 FM UC Berkeley',
        'http://icecast.media.berkeley.edu:8000/kalx-128.ogg'
        # 'http://icecast.media.berkeley.edu:8000/kalx-128.mp3'
    )

    kcrw = PlsEntry(
        'KCRW 89.9 FM Santa Monica',
        'http://kcrw.ic.llnwd.net/stream/kcrw_live')

    kcrw_24 = PlsEntry(
        'KCRW Music (Eclectic24)',
        'http://kcrw.ic.llnwd.net/stream/kcrw_music')

    kcrw_news = PlsEntry(
        'KCRW World News',
        'http://kcrw.ic.llnwd.net/stream/kcrw_mp3_128_news')

    kexp = PlsEntry(
        'KEXP 90.3 FM Seattle',
        'http://live-mp3-128.kexp.org:8000/')

    kpsu = PlsEntry(
        'KPSU 98.1 FM Portland State',
        'http://131.252.216.13:8080/listen'
    )

    kusf = PlsEntry(
        'KUSF San Fransisco',
        'http://104.236.145.45:8000/stream')

    kvrx = PlsEntry(
        'KVRX 91.7 FM Austin',
        'http://tstv-stream.tsm.utexas.edu:8000/kvrx_livestream'
    )

    kxlu = PlsEntry(
        'KXLU 88.9 FM Los Angeles',
        'http://www.ednixon.com:8120/stream')

    witr = PlsEntry(
        'WITR 89.7 FM Rochester',
        'http://streaming.witr.rit.edu:8000/live')

#   # Too quiet
#   wsou = PlsEntry(
#       'WSOU 89.5 FM Seton Hall',
#       'http://crystalout.surfernetwork.com:8001/WSOU_MP3')

#   # Too weird
#   wobc = PlsEntry(
#       'WOBC 91.5 Oberlin College',
#       'http://132.162.36.191:8000/listen')

    wers = PlsEntry(
        'WERS 88.9 FM Emerson College',
        'http://marconi.emerson.edu:8000/wers'
    )

    wgre = PlsEntry(
        'WGRW 91.5 FM DePauw',
        'http://184.154.90.186:8181'
    )

    nova = PlsEntry(
        'Radio Nova',
        'http://stream.radionova.no:80/fm993.mp3')

    kunnskap = PlsEntry(
        'Kunnskapstorget',
        'http://stream.radionova.no:80/kunnskapstoget.mp3')


class Other(PlaylistCollection):

    npr_24 = PlsEntry(
        'NPR 24 Hour Program Stream',
        'http://nprdmp.ic.llnwd.net/stream/nprdmp_live01_mp3')

    npr_music = PlsEntry(
        'NPR all songs considered',
        'http://nprdmp.ic.llnwd.net/stream/nprdmp_live21_mp3')

    punk = PlsEntry(
        'Punk FM',
        'http://46.28.49.164:7508/stream')

    mohawk = PlsEntry(
        'Mohawk Radio',
        'http://mohawkradio.kicks-ass.net:8000/')

    punks = PlsEntry(
        '12punks.FM',
        'http://listen.12punks.fm')


class BbcRadio(PlaylistCollection):
    """ BBC Radio """

    def __make_bbc_url(name):
        from time import time
        return 'http://bbcmedia.ic.llnwd.net/stream/{:s}'.format(
            'bbcmedia_{:s}_mf_p?s={:d}'.format(name, int(time())))

    radio1 = PlsEntry('BBC Radio 1', __make_bbc_url('radio1'))
    radio2 = PlsEntry('BBC Radio 2', __make_bbc_url('radio2'))
    radio3 = PlsEntry('BBC Radio 3 Classical', __make_bbc_url('radio3'))
    radio4 = PlsEntry('BBC Radio 4', __make_bbc_url('radio4fm'))
    radio5 = PlsEntry('BBC Radio 5 Live', __make_bbc_url('radio5live'))
    radio6 = PlsEntry('BBC Radio 6 Music', __make_bbc_url('6music'))


def config_parser_json(filename):
    import json
    data = {}
    with open('r', filename) as f:
        data = json.load(f)
    return data


def config_parser_yaml(filename):
    import yaml
    data = {}
    with open('r', filename) as f:
        data = yaml.load(f)
    return data


def config_parser_type(filename):
    f_ext = os.path.splitext(filename)[1]
    data = {}
    if f_ext in ('.yml', '.yaml'):
        data = config_parser_yaml(filename)
    elif f_ext in ('.json', '.js'):
        data = config_parser_json(filename)
    else:
        raise argparse.ArgumentTypeError(
            "Unknown file type '{!s}' ({!s})".format(f_ext, filename))

    print(repr(data))


if __name__ == '__main__':

    nrk = PlsPlaylist('NRK Radio')
    nrk.add('p1', NrkRadio.p1)
    nrk.add('p2', NrkRadio.p2)

    bbc = PlsPlaylist('BBC Radio')
    bbc.add('radio1', BbcRadio.radio1)
    bbc.add('radio2', BbcRadio.radio2)

    lists = PlsPlaylist('Lists', nrk=nrk, bbc=bbc)

    nrk = NrkRadio('nrk')
    bbc = BbcRadio('bbc')
    uni = UniRadio('uni')
    other = Other('other')

    group_map = {
        'bbc': bbc,
        'nrk': nrk,
        'uni': uni,
        'other': other,
    }
    #   default_selection = name_map.keys()
    #   for collection in name_map.values():
    #       for attr in collection.names:
    #           name_map[attr] = collection.get(attr)

    chan_map = dict()
    for collection in group_map.values():
        for attr in collection.names:
            chan_map[attr] = collection.get(attr)

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-l', '--list',
                        action='store_true',
                        default=False,
                        help="List channels")
    #   parser.add_argument('-c', '--config',
    #                       type=config_parser_type,
    #                       default=os.path.join(
    #                           os.path.dirname(os.path.abspath(__file__)),
    #                           'config.yml'))
    parser.add_argument('selection',
                        metavar='N',
                        choices=group_map.keys() + chan_map.keys() + ['all'],
                        nargs='*',
                        default='all',
                        help='Selection')

    args = parser.parse_args()

    entries = PlaylistCollection(None)
    if 'all' in args.selection:
        for gr in group_map:
            for attr in group_map[gr].names:
                entries.add(attr, group_map[gr].get(attr))
    else:
        for n in args.selection:
            if n in group_map:
                for attr in group_map[n].names:
                    entries.add(attr, group_map[n].get(attr))
            if n in chan_map:
                entries.add(n, chan_map[n])

    if args.list:
        for name in entries.names:
            print('{!s}: {!s}'.format(name, entries.get(name)))
        raise SystemExit()

    print(entries.pls())
    # PlaylistCollection.make_pls(entries)

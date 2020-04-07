from collections import namedtuple
from random import shuffle
from typing import List, Tuple

import logging
import functools
import pychromecast

pychromecast.IGNORE_CEC.append('*')


def _log(func):
    @functools.wraps(func)
    def magic(self, *args, **kwargs):
        assert self.selected_cast is not None
        res = func(self, *args, **kwargs)
        logging.info(func.__name__ + ' returned')
        logging.debug(self.selected_cast.media_controller.status)
        logging.debug(self.selected_cast.status)
        return res
    return magic


class PlayerController:
    def __init__(self):
        self.selected_cast = None
        self.music_list = []
        self.player_is_idle = None
        self.current_track = None
        self.cached_chromecasts = []

    def update_chromecast_list(self):
        self.cached_chromecasts = pychromecast.get_chromecasts()
        for cc in self.cached_chromecasts:
            logging.debug(cc.device)

        # TODO: if self.selected_cast not in cached_chromecasts?

    def select(self, idx):
        assert 0 <= idx < len(self.cached_chromecasts)
        self.selected_cast = self.cached_chromecasts[idx]

    def format_playlist(self):
        if not self.music_list:
            return "Пусто"
        playlist = 'Сейчас играет:\n' + self.current_track.title + '\n\nВ очереди:\n'
        playlist += '\n'.join([t for _, t, _ in self.music_list])
        return playlist

    def new_media_status(self, status):
        logging.debug("status_listener: %s", status)

        from pychromecast.controllers.media import MEDIA_PLAYER_STATE_UNKNOWN
        if status.player_state == MEDIA_PLAYER_STATE_UNKNOWN:
            return

        prev_idle = self.player_is_idle
        self.player_is_idle = status.player_is_idle
        if prev_idle is None:
            return
        # почему-то даже при новом урле источника duration остаётся прежним
        # и когда в начале трека прилетает статус с новым урлом в состоянии idle (баг?)
        # duration - единственная возможность отличить то, что мы ещё не начали играть новый трек
        # попробовать прицепиться к media_session_id?
        # status.duration может быть None
        if self.player_is_idle \
                and self.current_track.url == status.content_id \
                and self.current_track.duration == int(status.duration):
            self.play_next()

    def play_next(self):
        if len(self.music_list) == 0:
            return
        get_url, title, duration = self.music_list.pop(0)
        logging.info("Playing %s", title)
        Track = namedtuple('Track', ['url', 'title', 'duration'])
        self.current_track = Track(get_url(), title, duration // 1000)
        self.play_from_start(self.current_track.url)

    def shuffle(self):
        logging.info("Shuffling playlist")
        shuffle(self.music_list)

    def push(self, tracks: List[Tuple]):
        self.music_list.extend(tracks)
        if self.player_is_idle is None or self.player_is_idle is True:
            self.play_next()

    @_log
    def play_from_start(self, url):
        self.selected_cast.wait()
        logging.debug(self.selected_cast.status)
        mc = self.selected_cast.media_controller
        mc.register_status_listener(self)
        mc.play_media(url, 'audio/mp3')
        mc.block_until_active()
        mc.play()

    @_log
    def playpause(self):
        if self.selected_cast.media_controller.status.player_state == 'PLAYING':
            self.selected_cast.media_controller.pause()
            logging.info('pause')
        else:
            self.selected_cast.media_controller.play()
            logging.info('continue')

    @_log
    def volume_up(self):
        self.selected_cast.volume_up()

    @_log
    def volume_down(self):
        self.selected_cast.volume_down()

    @_log
    def repeat(self):
        self.play_from_start(self.current_track.url)

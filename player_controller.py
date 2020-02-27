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
        self.chromecasts = pychromecast.get_chromecasts()
        for cc in self.chromecasts:
            logging.debug(cc.device)
        self.selected_cast = None

    def select(self, idx):
        assert 0 <= idx < len(self.chromecasts)
        self.selected_cast = self.chromecasts[idx]

    @_log
    def play_from_start(self, url):
        self.selected_cast.wait()
        logging.debug(self.selected_cast.status)
        mc = self.selected_cast.media_controller
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
    def stop(self):
        self.selected_cast.media_controller.stop()

    @_log
    def volume_up(self):
        self.selected_cast.volume_up()

    @_log
    def volume_down(self):
        self.selected_cast.volume_down()

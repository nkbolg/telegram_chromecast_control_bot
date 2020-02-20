import pychromecast
import logging
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters
from telegram import Update, Bot, InlineKeyboardMarkup, InlineKeyboardButton
from yandex_music import Client

TOKEN = os.environ["CASTBOT_TOKEN"]
pychromecast.IGNORE_CEC.append('*')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
proxy = {
    'proxy_url': 'socks5://127.0.0.1:9150',
    'read_timeout': 26, 'connect_timeout': 27
}


class PlayerController:
    def __init__(self):
        self.chromecasts = pychromecast.get_chromecasts()
        for cc in self.chromecasts:
            logging.debug(cc.device)
        self.selected_cast = None

    def select(self, idx):
        assert 0 <= idx <= len(self.chromecasts)
        self.selected_cast = self.chromecasts[idx]

    def play_from_start(self, url):
        assert self.selected_cast is not None
        self.selected_cast.wait()
        logging.debug(self.selected_cast.status)
        mc = self.selected_cast.media_controller
        mc.play_media(url, 'audio/mp3')
        mc.block_until_active()
        mc.play()
        logging.info('playing')
        logging.debug(self.selected_cast.media_controller.status)
        logging.debug(self.selected_cast.status)

    def playpause(self):
        assert self.selected_cast is not None
        if self.selected_cast.media_controller.status.player_state == 'PLAYING':
            self.selected_cast.media_controller.pause()
            logging.info('pause')
        else:
            self.selected_cast.media_controller.play()
            logging.info('continue')
        logging.debug(self.selected_cast.media_controller.status)
        logging.debug(self.selected_cast.status)

    def stop(self):
        assert self.selected_cast is not None
        self.selected_cast.media_controller.stop()
        logging.info('stop')
        logging.debug(self.selected_cast.media_controller.status)
        logging.debug(self.selected_cast.status)

    def volume_up(self):
        assert self.selected_cast is not None
        self.selected_cast.volume_up()
        logging.info('volume_up')
        logging.debug(self.selected_cast.media_controller.status)
        logging.debug(self.selected_cast.status)

    def volume_down(self):
        assert self.selected_cast is not None
        self.selected_cast.volume_down()
        logging.info('volume_down')
        logging.debug(self.selected_cast.media_controller.status)
        logging.debug(self.selected_cast.status)


class BotController:
    def __init__(self, token):
        self.player_controller = PlayerController()
        self.updater = Updater(token, request_kwargs=proxy)
        self.last_song_url = None
        self.client = Client()
        dispatcher = self.updater.dispatcher
        dispatcher.add_handler(CommandHandler("start", self._start_callback))
        dispatcher.add_handler(CommandHandler("device", self._select_device_callback))
        dispatcher.add_handler(CallbackQueryHandler(self._device_query, pattern='device.*'))
        dispatcher.add_handler(CallbackQueryHandler(self._playback_control_query, pattern='playbackControl.*'))
        dispatcher.add_handler(MessageHandler(Filters.text, self._message_callback))

    def _get_track_info(self, track_url):
        album_id, track_id = track_url.split('/')[4:7:2]
        track = self.client.tracks(f"{track_id}:{album_id}")[0]
        friendly_name = f'{track.artists[0].name} - {track.title}'
        url = None
        for info in track.get_download_info():
            if info.codec == 'mp3':
                url = info.get_direct_link()
                break
        return url, friendly_name

    def _message_callback(self, bot: Bot, update: Update):
        chat_id = update.message.chat_id
        data = update.message.text
        url, track_title = self._get_track_info(data)
        button_list = [[
            InlineKeyboardButton('⏯️', callback_data='playbackControl playpause'),
            InlineKeyboardButton('⏹️', callback_data='playbackControl stop'),
            InlineKeyboardButton('🔊', callback_data='playbackControl volume_up'),
            InlineKeyboardButton('🔉', callback_data='playbackControl volume_down'),
            InlineKeyboardButton('🔁', callback_data='playbackControl repeat')
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        bot.send_message(chat_id=chat_id,
                         text=f"Сейчас играет — {track_title}",
                         reply_markup=reply_markup)
        self.player_controller.play_from_start(url)
        self.last_song_url = data

    def _start_callback(self, bot: Bot, update: Update):
        update.message.reply_text('Привет!\nВыбери колонки командой /device'
                                  '\nи отправляй ссылку на трек в Яндекс.Музыке🎵')

    def _select_device_callback(self, bot: Bot, update: Update):
        chat_id = update.message.chat_id
        button_list = [[InlineKeyboardButton(cc.device.friendly_name, callback_data=f'device {i}') for i, cc in enumerate(self.player_controller.chromecasts)]]
        reply_markup = InlineKeyboardMarkup(button_list)
        bot.send_message(chat_id,
                         text=f"Найдено {len(self.player_controller.chromecasts)} проигрывателя!\nВыберите:",
                         reply_markup=reply_markup)

    def _device_query(self, bot: Bot, update: Update):
        data = update.callback_query.data
        idx = int(data.split(' ')[1])
        self.player_controller.select(idx)

    def _playback_control_query(self, bot: Bot, update: Update):
        data = update.callback_query.data
        command = data.split(' ')[1]
        logging.info('playback_control_query: ', data)
        if command == 'playpause':
            self.player_controller.playpause()
        if command == 'stop':
            self.player_controller.stop()
        if command == 'volume_up':
            self.player_controller.volume_up()
        if command == 'volume_down':
            self.player_controller.volume_down()
        if command == 'repeat':
            assert self.last_song_url is not None
            url, _ = self._get_track_info(self.last_song_url)
            self.player_controller.play_from_start(url)

    def start_bot(self):
        self.updater.start_polling()

    def idle(self):
        self.updater.idle()


def main():
    bot = BotController(TOKEN)
    bot.start_bot()
    bot.idle()


if __name__ == '__main__':
    main()

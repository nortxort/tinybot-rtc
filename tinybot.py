# -*- coding: utf-8 -*-
""" Tinybot by Nortxort (https://github.com/nortxort/tinybot-rtc) """

import logging
import threading

import pinylib
from util import tracklist
from page import privacy
from apis import youtube, lastfm, other, locals_


__version__ = '1.0.6 (RTC)'
log = logging.getLogger(__name__)


class TinychatBot(pinylib.TinychatRTCClient):
    privacy_ = None
    timer_thread = None
    playlist = tracklist.PlayList()
    search_list = []
    is_search_list_yt_playlist = False

    @property
    def config_path(self):
        """ Returns the path to the rooms configuration directory. """
        return pinylib.CONFIG.CONFIG_PATH + self.room_name + '/'

    def on_joined(self, client_info):
        """
        Received when the client have joined the room successfully.

        :param client_info: This contains info about the client, such as user role and so on.
        :type client_info: dict
        """
        log.info('client info: %s' % client_info)
        self.client_id = client_info['handle']
        self.is_client_mod = client_info['mod']
        self.is_client_owner = client_info['owner']
        client = self.users.add(client_info)
        client.user_level = 0
        self.console_write(pinylib.COLOR['bright_green'], 'Client joined the room: %s:%s' % (client.nick, client.id))

        # do special operations.
        threading.Thread(target=self.options).start()

    def on_join(self, join_info):
        """
        Received when a user joins the room.

        :param join_info: This contains user information such as role, account and so on.
        :type join_info: dict
        """
        log.info('user join info: %s' % join_info)
        _user = self.users.add(join_info)
        if _user.account:
            if _user.is_owner:
                _user.user_level = 1
                self.console_write(pinylib.COLOR['red'], 'Room Owner %s:%d:%s' %
                                   (_user.nick, _user.id, _user.account))
            elif _user.is_mod:
                _user.user_level = 3
                self.console_write(pinylib.COLOR['bright_red'], 'Moderator %s:%d:%s' %
                                   (_user.nick, _user.id, _user.account))
            else:
                self.console_write(pinylib.COLOR['bright_yellow'], '%s:%d has account: %s' %
                                   (_user.nick, _user.id, _user.account))

                if _user.account in pinylib.CONFIG.B_ACCOUNT_BANS and self.is_client_mod:
                    if pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN:
                        self.send_kick_msg(_user.id)
                    else:
                        self.send_ban_msg(_user.id)
                    self.send_chat_msg('Auto-Banned: (bad account)')
                else:
                    tc_info = pinylib.apis.tinychat.user_info(_user.account)
                    if tc_info is not None:
                        _user.tinychat_id = tc_info['tinychat_id']
                        _user.last_login = tc_info['last_active']

        else:
            if _user.is_lurker and not pinylib.CONFIG.B_ALLOW_LURKERS and self.is_client_mod:
                if pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN:
                    self.send_kick_msg(_user.id)
                else:
                    self.send_ban_msg(_user.id)
                self.send_chat_msg('Auto-Banned: (lurkers not allowed)')

            elif not pinylib.CONFIG.B_ALLOW_GUESTS and self.is_client_mod:
                if pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN:
                    self.send_kick_msg(_user.id)
                else:
                    self.send_ban_msg(_user.id)
                self.send_chat_msg('Auto-Banned: (guests not allowed)')

        if pinylib.CONFIG.B_GREET and self.is_client_mod:
            if not _user.nick.startswith('guest-'):
                if _user.account:
                    self.send_chat_msg('Welcome to the room %s:%s:%s' %
                                       (_user.nick, _user.id, _user.account))
                else:
                    self.send_chat_msg('Welcome to the room %s:%s' % (_user.nick, _user.id))

        self.console_write(pinylib.COLOR['cyan'], '%s:%d joined the room.' % (_user.nick, _user.id))

    def on_nick(self, uid, nick):
        """
        Received when a user changes nick name.

        :param uid: The ID (handle) of the user.
        :type uid: int
        :param nick: The new nick name.
        :type nick: str
        """
        _user = self.users.search(uid)
        old_nick = _user.nick
        _user.nick = nick
        if uid != self.client_id:
            if _user.nick in pinylib.CONFIG.B_NICK_BANS:
                if pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN:
                    self.send_kick_msg(uid)
                else:
                    self.send_ban_msg(uid)
            else:
                if pinylib.CONFIG.B_GREET and self.is_client_mod:
                    if old_nick.startswith('guest-'):
                        if _user.account:
                            self.send_chat_msg('Welcome to the room %s:%s:%s' %
                                               (_user.nick, _user.id, _user.account))
                        else:
                            self.send_chat_msg('Welcome to the room %s:%s' % (_user.nick, _user.id))

                self.console_write(pinylib.COLOR['bright_cyan'], '%s:%s Changed nick to: %s' %
                                   (old_nick, uid, nick))

    def on_yut_play(self, yt_data):
        """
        Received when a youtube gets started or time searched.

        This also gets received when the client starts a youtube, the information is 
        however ignored in that case.

        :param yt_data: The event information contains info such as the ID (handle) of the user 
        starting/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        user_nick = 'n/a'
        if 'handle' in yt_data:
            if yt_data['handle'] != self.client_id:
                _user = self.users.search(yt_data['handle'])
                user_nick = _user.nick

        if self.playlist.has_active_track:
            self.cancel_timer()

        if yt_data['item']['offset'] == 0:
            # the video was started from the start. (start)
            _youtube = youtube.video_details(yt_data['item']['id'], False)
            self.playlist.start(user_nick, _youtube)
            self.timer(self.playlist.track.time)
            self.console_write(pinylib.COLOR['bright_magenta'], '%s started youtube video (%s)' %
                               (user_nick, yt_data['item']['id']))
        elif yt_data['item']['offset'] > 0:
            if user_nick == 'n/a':
                _youtube = youtube.video_details(yt_data['item']['id'], False)
                self.playlist.start(user_nick, _youtube)
                offset = self.playlist.play(yt_data['item']['offset'])
                self.timer(offset)
            else:
                offset = self.playlist.play(yt_data['item']['offset'])
                self.timer(offset)
                self.console_write(pinylib.COLOR['bright_magenta'], '%s searched the youtube video to: %s' %
                                   (user_nick, int(round(yt_data['item']['offset']))))

    def on_yut_pause(self, yt_data):
        """
        Received when a youtube gets paused or searched while paused.

        This also gets received when the client pauses or searches while paused, the information is 
        however ignored in that case.

        :param yt_data: The event information contains info such as the ID (handle) of the user 
        pausing/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        if 'handle' in yt_data:
            if yt_data['handle'] != self.client_id:
                _user = self.users.search(yt_data['handle'])
                if self.playlist.has_active_track:
                    self.cancel_timer()
                self.playlist.pause()
                self.console_write(pinylib.COLOR['bright_magenta'], '%s paused the video at %s' %
                                   (_user.nick, int(round(yt_data['item']['offset']))))

    def message_handler(self, msg):
        """
        A basic handler for chat messages.
        
        Overrides message_handler in pinylib
        to allow commands.

        :param msg: The chat message.
        :type msg: str
        """
        prefix = pinylib.CONFIG.B_PREFIX

        if msg.startswith(prefix):
            # Split the message in to parts.
            parts = msg.split(' ')
            # parts[0] is the command..
            cmd = parts[0].lower().strip()
            # The rest is a command argument.
            cmd_arg = ' '.join(parts[1:]).strip()

            if self.has_level(1):
                if self.is_client_owner:
                    if cmd == prefix + 'mod':
                        threading.Thread(target=self.do_make_mod, args=(cmd_arg,)).start()

                    elif cmd == prefix + 'rmod':
                        threading.Thread(target=self.do_remove_mod, args=(cmd_arg,)).start()

                    elif cmd == prefix + 'dir':
                        threading.Thread(target=self.do_directory).start()

                    elif cmd == prefix + 'p2t':
                        threading.Thread(target=self.do_push2talk).start()

                    elif cmd == prefix + 'crb':
                        threading.Thread(target=self.do_clear_room_bans).start()

                if cmd == prefix + 'kill':
                    self.do_kill()

                elif cmd == prefix + 'reboot':
                    self.do_reboot()

            if self.has_level(2):
                if cmd == prefix + 'mi':
                    self.do_media_info()

            if self.has_level(3):
                if cmd == prefix + 'op':
                    self.do_op_user(cmd_arg)

                elif cmd == prefix + 'deop':
                    self.do_deop_user(cmd_arg)

                elif cmd == prefix + 'noguest':
                    self.do_guests()

                elif cmd == prefix + 'lurkers':
                    self.do_lurkers()

                elif cmd == prefix + 'guestnick':
                    self.do_guest_nicks()

                elif cmd == prefix + 'greet':
                    self.do_greet()

                elif cmd == prefix + 'pub':
                    self.do_public_cmds()

                elif cmd == prefix == 'kab':
                    self.do_kick_as_ban()

                elif cmd == prefix + 'rs':
                    self.do_room_settings()

                elif cmd == prefix + 'top':
                    threading.Thread(target=self.do_lastfm_chart, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ran':
                    threading.Thread(target=self.do_lastfm_random_tunes, args=(cmd_arg,)).start()

                elif cmd == prefix + 'tag':
                    threading.Thread(target=self.do_search_lastfm_by_tag, args=(cmd_arg,)).start()

                elif cmd == prefix + 'pls':
                    threading.Thread(target=self.do_youtube_playlist_search, args=(cmd_arg,)).start()

                elif cmd == prefix + 'plp':
                    threading.Thread(target=self.do_play_youtube_playlist, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ssl':
                    self.do_show_search_list()

            if self.has_level(4):
                if cmd == prefix + 'skip':
                    self.do_skip()

                elif cmd == prefix + 'del':
                    self.do_delete_playlist_item(cmd_arg)

                elif cmd == prefix + 'rpl':
                    self.do_media_replay()

                elif cmd == prefix + 'mbpl':
                    self.do_play_media()

                elif cmd == prefix + 'mbpa':
                    self.do_media_pause()

                elif cmd == prefix + 'seek':
                    self.do_seek_media(cmd_arg)

                elif cmd == prefix + 'cm':
                    self.do_close_media()

                elif cmd == prefix + 'cpl':
                    self.do_clear_playlist()

                elif cmd == prefix + 'spl':
                    self.do_playlist_info()

                elif cmd == prefix + 'yts':
                    threading.Thread(target=self.do_youtube_search, args=(cmd_arg,)).start()

                elif cmd == prefix + 'pyts':
                    self.do_play_youtube_search(cmd_arg)

                elif cmd == prefix + 'clr':
                    self.do_clear()

                elif cmd == prefix + 'nick':
                    self.do_nick(cmd_arg)

                elif cmd == prefix + 'kick':
                    threading.Thread(target=self.do_kick, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ban':
                    threading.Thread(target=self.do_ban, args=(cmd_arg,)).start()

                elif cmd == prefix + 'bn':
                    self.do_bad_nick(cmd_arg)

                elif cmd == prefix + 'rmbn':
                    self.do_remove_bad_nick(cmd_arg)

                elif cmd == prefix + 'bs':
                    self.do_bad_string(cmd_arg)

                elif cmd == prefix + 'rmbs':
                    self.do_remove_bad_string(cmd_arg)

                elif cmd == prefix + 'ba':
                    self.do_bad_account(cmd_arg)

                elif cmd == prefix + 'rmba':
                    self.do_remove_bad_account(cmd_arg)

                elif cmd == prefix + 'list':
                    self.do_list_info(cmd_arg)

                elif cmd == prefix + 'uinfo':
                    self.do_user_info(cmd_arg)

                elif cmd == prefix + 'cam':
                    self.do_cam_approve(cmd_arg)

                elif cmd == prefix + 'close':
                    self.do_close_broadcast(cmd_arg)

            if (pinylib.CONFIG.B_PUBLIC_CMD and self.has_level(5)) or self.active_user.user_level < 5:
                if cmd == prefix + 'v':
                    self.do_version()

                elif cmd == prefix + 'help':
                    self.do_help()

                elif cmd == prefix + 't':
                    self.do_uptime()

                elif cmd == prefix + 'yt':
                    threading.Thread(target=self.do_play_youtube, args=(cmd_arg,)).start()

                elif cmd == prefix + 'q':
                    self.do_playlist_status()

                elif cmd == prefix + 'n':
                    self.do_next_tune_in_playlist()

                elif cmd == prefix + 'np':
                    self.do_now_playing()

                elif cmd == prefix + 'wp':
                    self.do_who_plays()

                # Tinychat API commands.
                elif cmd == prefix + 'spy':
                    threading.Thread(target=self.do_spy, args=(cmd_arg,)).start()

                elif cmd == prefix + 'acspy':
                    threading.Thread(target=self.do_account_spy, args=(cmd_arg,)).start()

                # Other API commands.
                elif cmd == prefix + 'urb':
                    threading.Thread(target=self.do_search_urban_dictionary, args=(cmd_arg,)).start()

                elif cmd == prefix + 'wea':
                    threading.Thread(target=self.do_weather_search, args=(cmd_arg,)).start()

                elif cmd == prefix + 'ip':
                    threading.Thread(target=self.do_whois_ip, args=(cmd_arg,)).start()

                # Just for fun.
                elif cmd == prefix + 'cn':
                    threading.Thread(target=self.do_chuck_noris).start()

                elif cmd == prefix + '8ball':
                    self.do_8ball(cmd_arg)

                elif cmd == prefix + 'roll':
                    self.do_dice()

                elif cmd == prefix + 'flip':
                    self.do_flip_coin()

            if cmd == prefix + 'pmme':
                self.do_pmme()

            # Print command to console.
            self.console_write(pinylib.COLOR['yellow'], self.active_user.nick + ': ' + cmd + ' ' + cmd_arg)
        else:
            #  Print chat message to console.
            self.console_write(pinylib.COLOR['green'], self.active_user.nick + ': ' + msg)
            # Only check chat msg for ban string if we are mod.
            if self.is_client_mod and self.active_user.user_level > 4:
                threading.Thread(target=self.check_msg, args=(msg,)).start()

        self.active_user.last_msg = msg

    # Level 1 Command methods.
    def do_make_mod(self, account):
        """ 
        Make a tinychat account a room moderator.

        :param account: The account to make a moderator.
        :type account: str
        """
        if self.is_client_owner:
            if len(account) is 0:
                self.send_chat_msg('Missing account name.')
            else:
                tc_user = self.privacy_.make_moderator(account)
                if tc_user is None:
                    self.send_chat_msg('The account is invalid.')
                elif not tc_user:
                    self.send_chat_msg('%s is already a moderator.' % account)
                elif tc_user:
                    self.send_chat_msg('%s was made a room moderator.' % account)

    def do_remove_mod(self, account):
        """ 
        Removes a tinychat account from the moderator list.

        :param account: The account to remove from the moderator list.
        :type account: str
        """
        if self.is_client_owner:
            if len(account) is 0:
                self.send_chat_msg('Missing account name.')
            else:
                tc_user = self.privacy_.remove_moderator(account)
                if tc_user:
                    self.send_chat_msg('%s is no longer a room moderator.' % account)
                elif not tc_user:
                    self.send_chat_msg('%s is not a room moderator.' % account)

    def do_directory(self):
        """ Toggles if the room should be shown on the directory. """
        if self.is_client_owner:
            if self.privacy_.show_on_directory():
                self.send_chat_msg('Room IS shown on the directory.')
            else:
                self.send_chat_msg('Room is NOT shown on the directory.')

    def do_push2talk(self):
        """ Toggles if the room should be in push2talk mode. """
        if self.is_client_owner:
            if self.privacy_.set_push2talk():
                self.send_chat_msg('Push2Talk is enabled.')
            else:
                self.send_chat_msg('Push2Talk is disabled.')

    def do_green_room(self):
        """ Toggles if the room should be in greenroom mode. """
        if self.is_client_owner:
            if self.privacy_.set_greenroom():
                self.send_chat_msg('Green room is enabled.')
            else:
                self.send_chat_msg('Green room is disabled.')

    def do_clear_room_bans(self):
        """ Clear all room bans. """
        # NOTE: This might not be needed in this version
        if self.is_client_owner:
            if self.privacy_.clear_bans():
                self.send_chat_msg('All room bans was cleared.')

    def do_kill(self):
        """ Kills the bot. """
        self.disconnect()

    def do_reboot(self):
        """ Reboots the bot. """
        self.reconnect()

    # Level 2 Command Methods.
    def do_media_info(self):
        """ Show information about the currently playing youtube. """
        if self.is_client_mod and self.playlist.has_active_track:
            self.send_chat_msg(
                'Playlist Tracks: ' + str(len(self.playlist.track_list)) + '\n' +
                'Track Title: ' + self.playlist.track.title + '\n' +
                'Track Index: ' + str(self.playlist.track_index) + '\n' +
                'Elapsed Track Time: ' + self.format_time(self.playlist.elapsed) + '\n' +
                'Remaining Track Time: ' + self.format_time(self.playlist.remaining)
            )

    # Level 3 Command Methods.
    def do_op_user(self, user_name):
        """ 
        Lets the room owner, a mod or a bot controller make another user a bot controller.

        :param user_name: The user to op.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is not None:
                    _user.user_level = 4
                    self.send_chat_msg('%s is now a bot controller (L4)' % user_name)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_deop_user(self, user_name):
        """ 
        Lets the room owner, a mod or a bot controller remove a user from being a bot controller.

        :param user_name: The user to deop.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is not None:
                    _user.user_level = 5
                    self.send_chat_msg('%s is not a bot controller anymore (L5)' % user_name)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_guests(self):
        """ Toggles if guests are allowed to join the room or not. """
        pinylib.CONFIG.B_ALLOW_GUESTS = not pinylib.CONFIG.B_ALLOW_GUESTS
        self.send_chat_msg('Allow Guests: %s' % pinylib.CONFIG.B_ALLOW_GUESTS)

    def do_lurkers(self):
        """ Toggles if lurkers are allowed or not. """
        pinylib.CONFIG.B_ALLOW_LURKERS = not pinylib.CONFIG.B_ALLOW_LURKERS
        self.send_chat_msg('Allowe Lurkers: %s' % pinylib.CONFIG.B_ALLOW_LURKERS)

    def do_guest_nicks(self):
        """ Toggles if guest nicks are allowed or not. """
        pinylib.CONFIG.B_ALLOW_GUESTS_NICKS = not pinylib.CONFIG.B_ALLOW_GUESTS_NICKS
        self.send_chat_msg('Allow Guest Nicks: %s' % pinylib.CONFIG.B_ALLOW_GUESTS_NICKS)

    def do_greet(self):
        """ Toggles if users should be greeted on entry. """
        pinylib.CONFIG.B_GREET = not pinylib.CONFIG.B_GREET
        self.send_chat_msg('Greet Users: %s' % pinylib.CONFIG.B_GREET)

    def do_public_cmds(self):
        """ Toggles if public commands are public or not. """
        pinylib.CONFIG.B_PUBLIC_CMD = not pinylib.CONFIG.B_PUBLIC_CMD
        self.send_chat_msg('Public Commands Enabled: %s' % pinylib.CONFIG.B_PUBLIC_CMD)

    def do_kick_as_ban(self):
        """ Toggles if kick should be used instead of ban for auto bans . """
        pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN = not pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN
        self.send_chat_msg('Use Kick As Auto Ban: %s' % pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN)

    def do_room_settings(self):
        """ Shows current room settings. """
        if self.is_client_owner:
            settings = self.privacy_.current_settings()
            self.send_chat_msg(
                'Broadcast Password: ' + settings['broadcast_pass'] + '\n' +
                'Room Password: ' + settings['room_pass'] + '\n' +
                'Login Type: ' + settings['allow_guest'] + '\n' +
                'Directory: ' + settings['show_on_directory'] + '\n' +
                'Push2Talk: ' + settings['push2talk'] + '\n' +
                'Greenroom: ' + settings['greenroom']
            )

    def do_lastfm_chart(self, chart_items):
        """
        Create a playlist from the most played tracks on last.fm.
        
        :param chart_items: The maximum amount of chart items. 
        :type chart_items: str | int
        """
        if self.is_client_mod:
            if len(chart_items) == 0 or chart_items is None:
                self.send_chat_msg('Please specify the max amount of tracks you want.')
            else:
                try:
                    chart_items = int(chart_items)
                except ValueError:
                    self.send_chat_msg('Only numbers allowed.')
                else:
                    if 0 < chart_items < 30:
                        self.send_chat_msg('Please wait while creating a playlist...')
                        _items = lastfm.chart(chart_items)
                        if _items is not None:
                            self.playlist.add_list(self.active_user.nick, _items)
                            self.send_chat_msg('Added ' + str(len(_items)) + 'tracks from last.fm chart.')
                            if not self.playlist.has_active_track:
                                track = self.playlist.next_track
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Failed to retrieve a result from last.fm.')
                    else:
                        self.send_chat_msg('No more than 30 tracks.')

    def do_lastfm_random_tunes(self, max_tracks):
        """
        Creates a playlist from what other people are listening to on last.fm
        
        :param max_tracks: The miximum amount of tracks.
        :type max_tracks: str | int
        """
        if self.is_client_mod:
            if len(max_tracks) == 0 or max_tracks is None:
                self.send_chat_msg('Please specify the max amount of tunes you want.')
            else:
                try:
                    max_tracks = int(max_tracks)
                except ValueError:
                    self.send_chat_msg('Only numbers allowed.')
                else:
                    if 0 < max_tracks < 50:
                        self.send_chat_msg('Please wait while creating playlist...')
                        _items = lastfm.listening_now(max_tracks)
                        if _items is not None:
                            self.playlist.add_list(self.active_user.nick, _items)
                            self.send_chat_msg('Added ' + str(len(_items)) + 'tracks from last.fm')
                            if not self.playlist.has_active_track:
                                track = self.playlist.next_track
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Failed to retrieve a result from last.fm.')
                    else:
                        self.send_chat_msg('No more than 50 tracks.')

    def do_search_lastfm_by_tag(self, search_str):
        """
        Search last.fm for tunes matching a tag.
        
        :param search_str: The search tag to search for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) == 0 or search_str is None:
                self.send_chat_msg('Missing search string.')
            else:
                self.send_chat_msg('Please wait while creating playlist..')
                _items = lastfm.tag_search(search_str)
                if _items is not None:
                    self.playlist.add_list(self.active_user.nick, _items)
                    self.send_chat_msg('Added ' + str(len(_items)) + 'tracks from last.fm')
                    if not self.playlist.has_active_track:
                        track = self.playlist.next_track
                        self.send_yut_play(track.id, track.time, track.title)
                        self.timer(track.time)
                else:
                    self.send_chat_msg('Failed to retrieve a result from last.fm.')

    def do_youtube_playlist_search(self, search_str):
        """
        Search youtube for a playlist.
        
        :param search_str: The search term to search for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) == 0:
                self.send_chat_msg('Missing search string.')
            else:
                self.search_list = youtube.playlist_search(search_str)
                if len(self.search_list) > 0:
                    self.is_search_list_yt_playlist = True
                    _ = '\n'.join('(%s) %s' % (i, d['playlist_title']) for i, d in enumerate(self.search_list))
                    self.send_chat_msg(_)
                else:
                    self.send_chat_msg('Failed to find playlist matching search term: %s' % search_str)

    def do_play_youtube_playlist(self, int_choice):
        """
        Play a previous searched playlist.
        
        :param int_choice: The index of the playlist.
        :type int_choice: str | int
        """
        if self.is_client_mod:
            if self.is_search_list_yt_playlist:
                try:
                    int_choice = int(int_choice)
                except ValueError:
                    self.send_chat_msg('Only numbers allowed.')
                else:
                    if 0 <= int_choice <= len(self.search_list) - 1:
                        self.send_chat_msg('Please wait while creating playlist..')
                        tracks = youtube.playlist_videos(self.search_list[int_choice])
                        if len(tracks) > 0:
                            self.playlist.add_list(self.active_user.nick, tracks)
                            self.send_chat_msg('Added %s tracks from youtube playlist.' % len(tracks))
                            if not self.playlist.has_active_track:
                                track = self.playlist.next_track
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Failed to retrieve videos from youtube playlist.')
                    else:
                        self.send_chat_msg('Please make a choice between 0-%s' % str(len(self.search_list) - 1))
            else:
                self.send_chat_msg('The search list does not contain any youtube playlist id\'s.')

    def do_show_search_list(self):
        """ Show what the search list contains. """
        if self.is_client_mod:
            if len(self.search_list) == 0:
                self.send_chat_msg('The search list is empty.')
            elif self.is_search_list_yt_playlist:
                _ = '\n'.join('(%s) - %s' % (i, d['playlist_title']) for i, d in enumerate(self.search_list))
                self.send_chat_msg('Youtube Playlist\'s\n' + _)
            else:
                _ = '\n'.join('(%s) %s %s' % (i, d['video_title'], self.format_time(d['video_time']))
                              for i, d in enumerate(self.search_list))
                self.send_chat_msg('Youtube Tracks\n' + _)

    # Level 4 Command Methods.
    def do_skip(self):
        """ Skip to the next item in the playlist. """
        if self.is_client_mod:
            if self.playlist.is_last_track is None:
                self.send_chat_msg('No tunes to skip. The playlist is empty.')
            elif self.playlist.is_last_track:
                self.send_chat_msg('This is the last track in the playlist.')
            else:
                self.cancel_timer()
                next_track = self.playlist.next_track
                self.send_yut_play(next_track.id, next_track.time, next_track.title)
                self.timer(next_track.time)

    def do_delete_playlist_item(self, to_delete):  # TODO: Make sure this is working.
        """
        Delete items from the playlist.
        
        :param to_delete: Item indexes to delete.
        :type to_delete: str
        """
        if self.is_client_mod:
            if len(self.playlist.track_list) == 0:
                self.send_chat_msg('The playlist is empty.')
            elif len(to_delete) == 0:
                self.send_chat_msg('No indexes provided.')
            else:
                indexes = None
                by_range = False

                try:
                    if ':' in to_delete:
                        range_indexes = map(int, to_delete.split(':'))
                        temp_indexes = range(range_indexes[0], range_indexes[1] + 1)
                        if len(temp_indexes) > 1:
                            by_range = True
                    else:
                        temp_indexes = map(int, to_delete.split(','))
                except ValueError as ve:
                    log.error('wrong format: %s' % ve)
                else:
                    indexes = []
                    for i in temp_indexes:
                        if i < len(self.playlist.track_list) and i not in indexes:
                            indexes.append(i)

                if indexes is not None and len(indexes) > 0:
                    result = self.playlist.delete(indexes, by_range)
                    if result is not None:
                        if by_range:
                            self.send_chat_msg('Deleted from index: %s to index: %s' %
                                               (result['from'], result['to']))
                        elif result['deleted_indexes_len'] is 1:
                            self.send_chat_msg('Deleted %s' % result['track_title'])
                        else:
                            self.send_chat_msg('Deleted tracks at index: %s' %
                                               ', '.join(result['deleted_indexes']))
                    else:
                        self.send_chat_msg('Nothing was deleted.')

    def do_media_replay(self):
        """ Replay the currently playing track. """
        if self.is_client_mod:
            if self.playlist.track is not None:
                self.cancel_timer()
                track = self.playlist.replay()
                self.send_yut_play(track.id, track.time, track.title)
                self.timer(track.time)

    def do_play_media(self):
        """ Play a track on pause . """
        if self.is_client_mod:
            if self.playlist.track is not None:
                if self.playlist.has_active_track:
                    self.cancel_timer()
                if self.playlist.is_paused:
                    self.playlist.play(self.playlist.elapsed)
                    self.send_yut_play(self.playlist.track.id, self.playlist.track.time,
                                       self.playlist.track.title, self.playlist.elapsed)  #
                    self.timer(self.playlist.remaining)

    def do_media_pause(self):
        """ Pause a track. """
        if self.is_client_mod:
            track = self.playlist.track
            if track is not None:
                if self.playlist.has_active_track:
                    self.cancel_timer()
                self.playlist.pause()
                self.send_yut_pause(track.id, track.time, self.playlist.elapsed)

    def do_close_media(self):
        """ Close a track playing. """
        if self.is_client_mod:
            if self.playlist.has_active_track:
                self.cancel_timer()
                self.playlist.stop()
                self.send_yut_stop(self.playlist.track.id, self.playlist.track.time, self.playlist.elapsed)

    def do_seek_media(self, time_point):
        """
        Time search a track.
        
        :param time_point: The time point in which to search to.
        :type time_point: str
        """
        if self.is_client_mod:
            if ('h' in time_point) or ('m' in time_point) or ('s' in time_point):
                offset = pinylib.string_util.convert_to_seconds(time_point)
                if offset == 0:
                    self.send_chat_msg('Invalid seek time.')
                else:
                    track = self.playlist.track
                    if track is not None:
                        if 0 < offset < track.time:
                            if self.playlist.has_active_track:
                                self.cancel_timer()
                            if self.playlist.is_paused:
                                self.playlist.pause(offset=offset)  #
                                self.send_yut_pause(track.id, track.time, offset)
                            else:
                                self.playlist.play(offset)
                                self.send_yut_play(track.id, track.time, track.title, offset)
                                self.timer(self.playlist.remaining)

    def do_clear_playlist(self):
        """ Clear the playlist for items."""
        if self.is_client_mod:
            if len(self.playlist.track_list) > 0:
                pl_length = str(len(self.playlist.track_list))
                self.playlist.clear()
                self.send_chat_msg('Deleted %s items in the playlist.' % pl_length)
            else:
                self.send_chat_msg('The playlist is empty, nothing to delete.')

    def do_playlist_info(self):  # TODO: this needs more work !
        """ Shows the next tracks in the playlist. """
        if self.is_client_mod:
            if len(self.playlist.track_list) > 0:
                tracks = self.playlist.get_tracks()
                if len(tracks) > 0:
                    # If i is 0 then mark that as the next track
                    _ = '\n'.join('(%s) - %s %s' % (track[0], track[1].title, self.format_time(track[1].time))
                                  for i, track in enumerate(tracks))
                    self.send_chat_msg(_)

    def do_youtube_search(self, search_str):
        """ 
        Search youtube for a list of matching candidates.
        
        :param search_str: The search term to search for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) == 0:
                self.send_chat_msg('Missing search string.')
            else:
                self.search_list = youtube.search_list(search_str, results=5)
                if len(self.search_list) > 0:
                    self.is_search_list_yt_playlist = False
                    _ = '\n'.join('(%s) %s %s' % (i, d['video_title'], self.format_time(d['video_time']))
                                  for i, d in enumerate(self.search_list))  #
                    self.send_chat_msg(_)
                else:
                    self.send_chat_msg('Could not find anything matching: %s' % search_str)

    def do_play_youtube_search(self, int_choice):
        """
        Play a track from a previous youtube search list.
        
        :param int_choice: The index of the track in the search.
        :type int_choice: str | int
        """
        if self.is_client_mod:
            if not self.is_search_list_yt_playlist:
                if len(self.search_list) > 0:
                    try:
                        int_choice = int(int_choice)
                    except ValueError:
                        self.send_chat_msg('Only numbers allowed.')
                    else:
                        if 0 <= int_choice <= len(self.search_list) - 1:

                            if self.playlist.has_active_track:
                                track = self.playlist.add(self.active_user.nick, self.search_list[int_choice])
                                self.send_chat_msg('Added (%s) %s %s' %
                                                   (self.playlist.last_index,
                                                    track.title, self.format_time(track.time)))
                            else:
                                track = self.playlist.start(self.active_user.nick, self.search_list[int_choice])
                                self.send_yut_play(track.id, track.time, track.title)
                                self.timer(track.time)
                        else:
                            self.send_chat_msg('Please make a choice between 0-%s' % str(len(self.search_list) - 1))
                else:
                    self.send_chat_msg('No youtube track id\'s in the search list.')
            else:
                self.send_chat_msg('The search list only contains youtube playlist id\'s.')

    def do_clear(self):
        """ Clears the chat box. """
        self.send_chat_msg('_\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n'
                           '\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n_')

    def do_nick(self, new_nick):
        """ 
        Set a new nick for the bot.

        :param new_nick: The new nick name.
        :type new_nick: str
        """
        if len(new_nick) is 0:
            self.nickname = pinylib.string_util.create_random_string(5, 25)
            self.set_nick()
        else:
            self.nickname = new_nick
            self.set_nick()

    def do_kick(self, user_name):
        """ 
        Kick a user out of the room.

        :param user_name: The username to kick.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            elif user_name == self.nickname:
                self.send_chat_msg('Action not allowed.')
            else:
                if user_name.startswith('*'):
                    user_name = user_name.replace('*', '')
                    _users = self.users.search_containing(user_name)
                    if len(_users) > 0:
                        for i, user in enumerate(_users):
                            if user.nick != self.nickname and user.user_level > self.active_user.user_level:
                                if i <= pinylib.CONFIG.B_MAX_MATCH_BANS - 1:
                                    self.send_kick_msg(user.id)
                else:
                    _user = self.users.search_by_nick(user_name)
                    if _user is None:
                        self.send_chat_msg('No user named: %s' % user_name)
                    elif _user.user_level < self.active_user.user_level:
                        self.send_chat_msg('Not allowed.')
                    else:
                        self.send_kick_msg(_user.id)

    def do_ban(self, user_name):
        """ 
        Ban a user from the room.

        :param user_name: The username to ban.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            elif user_name == self.nickname:
                self.send_chat_msg('Action not allowed.')
            else:
                if user_name.startswith('*'):
                    user_name = user_name.replace('*', '')
                    _users = self.users.search_containing(user_name)
                    if len(_users) > 0:
                        for i, user in enumerate(_users):
                            if user.nick != self.nickname and user.user_level > self.active_user.user_level:
                                if i <= pinylib.CONFIG.B_MAX_MATCH_BANS - 1:
                                    self.send_ban_msg(user.id)
                else:
                    _user = self.users.search_by_nick(user_name)
                    if _user is None:
                        self.send_chat_msg('No user named: %s' % user_name)
                    elif _user.user_level < self.active_user.user_level:
                        self.send_chat_msg('Not allowed.')
                    else:
                        self.send_ban_msg(_user.id)

    def do_bad_nick(self, bad_nick):
        """ 
        Adds a username to the nick bans file.

        :param bad_nick: The bad nick to write to the nick bans file.
        :type bad_nick: str
        """
        if self.is_client_mod:
            if len(bad_nick) is 0:
                self.send_chat_msg('Missing username.')
            elif bad_nick in pinylib.CONFIG.B_NICK_BANS:
                self.send_chat_msg('%s is already in list.' % bad_nick)
            else:
                pinylib.file_handler.file_writer(self.config_path,
                                                 pinylib.CONFIG.B_NICK_BANS_FILE_NAME, bad_nick)
                self.send_chat_msg('%s was added to file.' % bad_nick)
                self.load_list(nicks=True)

    def do_remove_bad_nick(self, bad_nick):
        """ 
        Removes nick from the nick bans file.

        :param bad_nick: The bad nick to remove from the nick bans file.
        :type bad_nick: str
        """
        if self.is_client_mod:
            if len(bad_nick) is 0:
                self.send_chat_msg('Missing username')
            else:
                if bad_nick in pinylib.CONFIG.B_NICK_BANS:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_NICK_BANS_FILE_NAME,
                                                                bad_nick)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_nick)
                        self.load_list(nicks=True)

    def do_bad_string(self, bad_string):
        """ 
        Adds a string to the string bans file.

        :param bad_string: The bad string to add to the string bans file.
        :type bad_string: str
        """
        if self.is_client_mod:
            if len(bad_string) is 0:
                self.send_chat_msg('Ban string can\'t be blank.')
            elif len(bad_string) < 3:
                self.send_chat_msg('Ban string to short: ' + str(len(bad_string)))
            elif bad_string in pinylib.CONFIG.B_STRING_BANS:
                self.send_chat_msg('%s is already in list.' % bad_string)
            else:
                pinylib.file_handler.file_writer(self.config_path,
                                                 pinylib.CONFIG.B_STRING_BANS_FILE_NAME, bad_string)
                self.send_chat_msg('%s was added to file.' % bad_string)
                self.load_list(strings=True)

    def do_remove_bad_string(self, bad_string):
        """ 
        Removes a string from the string bans file.

        :param bad_string: The bad string to remove from the string bans file.
        :type bad_string: str
        """
        if self.is_client_mod:
            if len(bad_string) is 0:
                self.send_chat_msg('Missing word string.')
            else:
                if bad_string in pinylib.CONFIG.B_STRING_BANS:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_STRING_BANS_FILE_NAME,
                                                                bad_string)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_string)
                        self.load_list(strings=True)

    def do_bad_account(self, bad_account_name):
        """ 
        Adds an account name to the account bans file.

        :param bad_account_name: The bad account name to add to the account bans file.
        :type bad_account_name: str
        """
        if self.is_client_mod:
            if len(bad_account_name) is 0:
                self.send_chat_msg('Account can\'t be blank.')
            elif len(bad_account_name) < 3:
                self.send_chat_msg('Account to short: ' + str(len(bad_account_name)))
            elif bad_account_name in pinylib.CONFIG.B_ACCOUNT_BANS:
                self.send_chat_msg('%s is already in list.' % bad_account_name)
            else:
                pinylib.file_handler.file_writer(self.config_path,
                                                 pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME,
                                                 bad_account_name)
                self.send_chat_msg('%s was added to file.' % bad_account_name)
                self.load_list(accounts=True)

    def do_remove_bad_account(self, bad_account):
        """ 
        Removes an account from the account bans file.

        :param bad_account: The badd account name to remove from account bans file.
        :type bad_account: str
        """
        if self.is_client_mod:
            if len(bad_account) is 0:
                self.send_chat_msg('Missing account.')
            else:
                if bad_account in pinylib.CONFIG.B_ACCOUNT_BANS:
                    rem = pinylib.file_handler.remove_from_file(self.config_path,
                                                                pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME,
                                                                bad_account)
                    if rem:
                        self.send_chat_msg('%s was removed.' % bad_account)
                        self.load_list(accounts=True)

    def do_list_info(self, list_type):
        """ 
        Shows info of different lists/files.

        :param list_type: The type of list to find info for.
        :type list_type: str
        """
        if self.is_client_mod:
            if len(list_type) is 0:
                self.send_chat_msg('Missing list type.')
            else:
                if list_type.lower() == 'bn':
                    if len(pinylib.CONFIG.B_NICK_BANS) is 0:
                        self.send_chat_msg('No items in this list.')
                    else:
                        self.send_chat_msg('%s nicks bans in list.' % len(pinylib.CONFIG.B_NICK_BANS))

                elif list_type.lower() == 'bs':
                    if len(pinylib.CONFIG.B_STRING_BANS) is 0:
                        self.send_chat_msg('No items in this list.')
                    else:
                        self.send_chat_msg('%s string bans in list.' % pinylib.CONFIG.B_STRING_BANS)

                elif list_type.lower() == 'ba':
                    if len(pinylib.CONFIG.B_ACCOUNT_BANS) is 0:
                        self.send_chat_msg('No items in this list.')
                    else:
                        self.send_chat_msg('%s account bans in list.' % pinylib.CONFIG.B_ACCOUNT_BANS)

                elif list_type.lower() == 'mods':
                    if self.is_client_owner:
                        if len(self.privacy_.room_moderators) is 0:
                            self.send_chat_msg('There is currently no moderators for this room.')
                        elif len(self.privacy_.room_moderators) is not 0:
                            mods = ', '.join(self.privacy_.room_moderators)
                            self.send_chat_msg('Moderators: ' + mods)

    def do_user_info(self, user_name):
        """ 
        Shows user object info for a given user name.

        :param user_name: The user name of the user to show the info for.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) is 0:
                self.send_chat_msg('Missing username.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is None:
                    self.send_chat_msg('No user named: %s' % user_name)
                else:
                    if _user.account and _user.tinychat_id is None:
                        user_info = pinylib.apis.tinychat.user_info(_user.account)
                        if user_info is not None:
                            _user.tinychat_id = user_info['tinychat_id']
                            _user.last_login = user_info['last_active']
                    online_time = (pinylib.time.time() - _user.join_time)

                    info = [
                        'User Level: ' + str(_user.user_level),
                        'Online Time: ' + self.format_time(online_time),
                        'Last Message: ' + str(_user.last_msg)
                    ]
                    if _user.tinychat_id is not None:
                        info.append('Account: ' + str(_user.account))
                        info.append('Tinychat ID: ' + str(_user.tinychat_id))
                        info.append('Last Login: ' + _user.last_login)

                    self.send_chat_msg('\n'.join(info))

    def do_cam_approve(self, user_name):
        """
        Allow a user to broadcast in a green room enabled room.

        :param user_name:  The name of the user allowed to broadcast.
        :type user_name: str
        """
        if self.is_green_room and self.is_client_mod:
            if len(user_name) == 0 and self.active_user.is_waiting:
                self.send_cam_approve_msg(self.active_user.id)
            elif len(user_name) > 0:
                _user = self.users.search_by_nick(user_name)
                if _user is not None and _user.is_waiting:
                    self.send_cam_approve_msg(_user.id)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    def do_close_broadcast(self, user_name):
        """
        Close a users broadcast.

        :param user_name: The name of the user to close.
        :type user_name: str
        """
        if self.is_client_mod:
            if len(user_name) == 0:
                self.send_chat_msg('Mising user name.')
            else:
                _user = self.users.search_by_nick(user_name)
                if _user is not None and _user.is_broadcasting:
                    self.send_close_user_msg(_user.id)
                else:
                    self.send_chat_msg('No user named: %s' % user_name)

    # Public (Level 5) Command Methods.
    def do_playlist_status(self):
        """ Shows the playlist queue. """
        if self.is_client_mod:
            if len(self.playlist.track_list) == 0:
                self.send_chat_msg('The playlist is empty.')
            else:
                queue = self.playlist.queue
                if queue is not None:
                    self.send_chat_msg('%s items in the playlist, %s still in queue.' %
                                       (queue[0], queue[1]))

    def do_next_tune_in_playlist(self):
        """ Shows the next track in the playlist. """
        if self.is_client_mod:
            if self.playlist.is_last_track is None:
                self.send_chat_msg('The playlist is empty.')
            elif self.playlist.is_last_track:
                self.send_chat_msg('This is the last track.')
            else:
                pos, next_track = self.playlist.next_track_info()
                if next_track is not None:
                    self.send_chat_msg('(%s) %s %s' %
                                       (pos, next_track.title, self.format_time(next_track.time)))

    def do_now_playing(self):
        """ Shows what track is currently playing. """
        if self.is_client_mod:
            if self.playlist.has_active_track:
                track = self.playlist.track
                if len(self.playlist.track_list) > 0:
                    self.send_private_msg(self.active_user.id,
                                          '(%s) %s %s' % (self.playlist.current_index, track.title,
                                                          self.format_time(track.time)))
                else:
                    self.send_private_msg(self.active_user.id, '%s %s' %
                                          (track.title, self.format_time(track.time)))
            else:
                self.send_private_msg(self.active_user.nick, 'No track playing.')

    def do_who_plays(self):
        """ Show who requested the currently playing track. """
        if self.is_client_mod:
            if self.playlist.has_active_track:
                track = self.playlist.track
                ago = self.format_time(int(pinylib.time.time() - track.rq_time))
                self.send_chat_msg('%s requested this track %s ago.' % (track.owner, ago))
            else:
                self.send_chat_msg('No track playing.')

    def do_version(self):
        """ Show version info. """
        self.send_private_msg(self.active_user.id, 'tinybot %s pinylib %s' %
                              (__version__, pinylib.__version__))

    def do_help(self):
        """ Posts a link to github readme/wiki or other page about the bot commands. """
        self.send_private_msg(self.active_user.id,
                              'Help: https://github.com/nortxort/tinybot-rtc/wiki/commands')

    def do_uptime(self):
        """ Shows the bots uptime. """
        self.send_chat_msg('Bot-Uptime: ' + self.format_time(self.get_runtime()))

    def do_pmme(self):
        """ Opens a PM session with the bot. """
        self.send_private_msg(self.active_user.id, 'How can i help you %s?' % self.active_user.nick)

    def do_play_youtube(self, search_str):
        """ 
        Plays a youtube video matching the search term.

        :param search_str: The search term.
        :type search_str: str
        """
        log.info('user: %s:%s is searching youtube: %s' % (self.active_user.nick, self.active_user.id, search_str))
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_chat_msg('Please specify youtube title, id or link.')
            else:
                _youtube = youtube.search(search_str)
                if _youtube is None:
                    log.warning('youtube request returned: %s' % _youtube)
                    self.send_chat_msg('Could not find video: ' + search_str)
                else:
                    log.info('youtube found: %s' % _youtube)
                    if self.playlist.has_active_track:
                        track = self.playlist.add(self.active_user.nick, _youtube)
                        self.send_chat_msg('(%s) %s %s' %
                                           (self.playlist.last_index, track.title, self.format_time(track.time)))
                    else:
                        track = self.playlist.start(self.active_user.nick, _youtube)
                        self.send_yut_play(track.id, track.time, track.title)
                        self.timer(track.time)

    # == Tinychat API Command Methods. ==
    def do_spy(self, roomname):
        """ 
        Shows info for a given room.

        :param roomname: The room name to find spy info for.
        :type roomname: str
        """
        if self.is_client_mod:
            if len(roomname) is 0:
                self.send_chat_msg('Missing room name.')
            else:
                spy_info = pinylib.apis.tinychat.spy_info(roomname)
                if spy_info is None:
                    self.send_chat_msg('Failed to retrieve information.')
                elif 'error' in spy_info:
                    self.send_chat_msg(spy_info['error'])
                else:
                    self.send_chat_msg('Mods: %s, \nBroadcasters: %s, \nUsers: %s' %
                                       (spy_info['mod_count'], spy_info['broadcaster_count'],
                                        spy_info['total_count']))
                    if self.has_level(3):
                        users = ', '.join(spy_info['users'])
                        self.send_chat_msg(users)

    def do_account_spy(self, account):
        """ 
        Shows info about a tinychat account.

        :param account: tinychat account.
        :type account: str
        """
        if self.is_client_mod:
            if len(account) is 0:
                self.send_chat_msg('Missing username to search for.')
            else:
                tc_usr = pinylib.apis.tinychat.user_info(account)
                if tc_usr is None:
                    self.send_chat_msg('Could not find tinychat info for: %s' % account)
                else:
                    self.send_chat_msg('ID: %s, \nLast Login: %s' %
                                       (tc_usr['tinychat_id'], tc_usr['last_active']))

    # == Other API Command Methods. ==
    def do_search_urban_dictionary(self, search_str):
        """ 
        Shows urbandictionary definition of search string.

        :param search_str: The search string to look up a definition for.
        :type search_str: str
        """
        if self.is_client_mod:
            if len(search_str) is 0:
                self.send_chat_msg('Please specify something to look up.')
            else:
                urban = other.urbandictionary_search(search_str)
                if urban is None:
                    self.send_chat_msg('Could not find a definition for: %s' % search_str)
                else:
                    if len(urban) > 70:
                        chunks = pinylib.string_util.chunk_string(urban, 70)
                        for i in range(0, 2):
                            self.send_chat_msg(chunks[i])
                    else:
                        self.send_chat_msg(urban)

    def do_weather_search(self, search_str):
        """ 
        Shows weather info for a given search string.

        :param search_str: The search string to find weather data for.
        :type search_str: str
        """
        if len(search_str) is 0:
            self.send_chat_msg('Please specify a city to search for.')
        else:
            weather = other.weather_search(search_str)
            if weather is None:
                self.send_chat_msg('Could not find weather data for: %s' % search_str)
            else:
                self.send_chat_msg(weather)

    def do_whois_ip(self, ip_str):
        """ 
        Shows whois info for a given ip address or domain.

        :param ip_str: The ip address or domain to find info for.
        :type ip_str: str
        """
        if len(ip_str) is 0:
            self.send_chat_msg('Please provide an IP address or domain.')
        else:
            whois = other.whois(ip_str)
            if whois is None:
                self.send_chat_msg('No info found for: %s' % ip_str)
            else:
                self.send_chat_msg(whois)

    # == Just For Fun Command Methods. ==
    def do_chuck_noris(self):
        """ Shows a chuck norris joke/quote. """
        chuck = other.chuck_norris()
        if chuck is not None:
            self.send_chat_msg(chuck)

    def do_8ball(self, question):
        """ 
        Shows magic eight ball answer to a yes/no question.

        :param question: The yes/no question.
        :type question: str
        """
        if len(question) is 0:
            self.send_chat_msg('Question.')
        else:
            self.send_chat_msg('8Ball %s' % locals_.eight_ball())

    def do_dice(self):
        """ roll the dice. """
        self.send_chat_msg('The dice rolled: %s' % locals_.roll_dice())

    def do_flip_coin(self):
        """ Flip a coin. """
        self.send_chat_msg('The coin was: %s' % locals_.flip_coin())

    def private_message_handler(self, private_msg):
        """
        Private message handler.
        
        Overrides private_message_handler in pinylib
        to enable private commands.
        
        :param private_msg: The private message.
        :type private_msg: str
        """
        prefix = pinylib.CONFIG.B_PREFIX
        # Split the message in to parts.
        pm_parts = private_msg.split(' ')
        # parts[0] is the command..
        pm_cmd = pm_parts[0].lower().strip()
        # The rest is a command argument.
        pm_arg = ' '.join(pm_parts[1:]).strip()

        if self.has_level(1):
            if self.is_client_owner:
                pass

            if pm_cmd == prefix + 'key':
                self.do_key(pm_arg)

            elif pm_cmd == prefix + 'clrbn':
                self.do_clear_bad_nicks()

            elif pm_cmd == prefix + 'clrbs':
                self.do_clear_bad_strings()

            elif pm_cmd == prefix + 'clrba':
                self.do_clear_bad_accounts()

        # Public commands.
        if self.has_level(5):
            if pm_cmd == prefix + 'opme':
                self.do_opme(pm_arg)

        # Print to console.
        msg = str(private_msg).replace(pinylib.CONFIG.B_KEY, '***KEY***'). \
            replace(pinylib.CONFIG.B_SUPER_KEY, '***SUPER KEY***')

        self.console_write(pinylib.COLOR['white'], 'Private message from %s: %s' % (self.active_user.nick, msg))

    def do_key(self, new_key):
        """
        Shows or sets a new secret bot controller key.
        
        :param new_key: The new secret key.
        :type new_key: str
        """
        if len(new_key) == 0:
            self.send_private_msg(self.active_user.id, 'The current secret key is: %s' % pinylib.CONFIG.B_KEY)
        elif len(new_key) < 6:
            self.send_private_msg(self.active_user.id, 'The key is to short, it must be atleast 6 characters long.'
                                                       'It is %s long.' % len(new_key))
        elif len(new_key) >= 6:
            # reset current bot controllers.
            for user in self.users.all:
                if self.users.all[user].user_level is 2 or self.users.all[user].user_level is 4:
                    self.users.all[user].user_level = 5

            pinylib.CONFIG.B_KEY = new_key
            self.send_private_msg(self.active_user.id, 'The key was changed to: %s' % new_key)

    def do_clear_bad_nicks(self):
        """ Clear the nick bans file. """
        pinylib.CONFIG.B_NICK_BANS[:] = []
        pinylib.file_handler.delete_file_content(self.config_path, pinylib.CONFIG.B_NICK_BANS_FILE_NAME)

    def do_clear_bad_strings(self):
        """ Clear the string bans file. """
        pinylib.CONFIG.B_STRING_BANS[:] = []
        pinylib.file_handler.delete_file_content(self.config_path, pinylib.CONFIG.B_STRING_BANS_FILE_NAME)

    def do_clear_bad_accounts(self):
        """ Clear the account bans file. """
        pinylib.CONFIG.B_ACCOUNT_BANS[:] = []
        pinylib.file_handler.delete_file_content(self.config_path, pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME)

    def do_opme(self, key):
        """
        Make a user a bot controller if the correct key is provided.
        
        :param key: The secret bot controller key.
        :type key: str
        """
        if len(key) == 0:
            self.send_private_msg(self.active_user.id, 'Missing key.')
        elif key == pinylib.CONFIG.B_SUPER_KEY:
            if self.is_client_owner:
                self.active_user.user_level = 1
                self.send_private_msg(self.active_user.id, 'You are now a super mod.')
            else:
                self.send_private_msg(self.active_user.id, 'The client is not using the owner account.')
        elif key == pinylib.CONFIG.B_KEY:
            if self.is_client_mod:
                self.active_user.user_level = 2
                self.send_private_msg(self.active_user.id, 'You are now a bot controller.')
            else:
                self.send_private_msg(self.active_user.id, 'The client is not moderator.')
        else:
            self.send_private_msg(self.active_user.id, 'Wrong key.')

    # Timer Related.
    def timer_event(self):
        """ This gets called when the timer has reached the time. """
        if len(self.playlist.track_list) > 0:
            if self.playlist.is_last_track:
                if self.is_connected:
                    self.send_chat_msg('Resetting playlist.')
                self.playlist.clear()
            else:
                track = self.playlist.next_track
                if track is not None and self.is_connected:
                    self.send_yut_play(track.id, track.time, track.title)
                self.timer(track.time)

    def timer(self, event_time):
        """
        Track event timer.
        
        This will cause an event to occur once the time is done.
        
        :param event_time: The time in seconds for when an event should occur.
        :type event_time: int | float
        """
        self.timer_thread = threading.Timer(event_time, self.timer_event)
        self.timer_thread.start()

    def cancel_timer(self):
        """ Cancel the track timer. """
        if self.timer_thread is not None:
            if self.timer_thread.is_alive():
                self.timer_thread.cancel()
                self.timer_thread = None
                return True
            return False
        return False

    # Helper Methods.
    def options(self):
        """ Load/set special options. """
        log.info('options: is_client_owner: %s, is_client_mod: %s' % (self.is_client_owner, self.is_client_mod))
        if self.is_client_owner:
            self.get_privacy_settings()
        if self.is_client_mod:
            self.send_banlist_msg()
            self.load_list(nicks=True, accounts=True, strings=True)

    def get_privacy_settings(self):
        """ Parse the privacy settings page. """
        log.info('Parsing %s\'s privacy page.' % self.account)
        self.privacy_ = privacy.Privacy(proxy=None)
        self.privacy_.parse_privacy_settings()

    def load_list(self, nicks=False, accounts=False, strings=False):
        """
        Loads different list to memory.
        
        :param nicks: bool, True load nick bans file.
        :param accounts: bool, True load account bans file.
        :param strings: bool, True load ban strings file.
        """
        if nicks:
            pinylib.CONFIG.B_NICK_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                          pinylib.CONFIG.B_NICK_BANS_FILE_NAME)
        if accounts:
            pinylib.CONFIG.B_ACCOUNT_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                             pinylib.CONFIG.B_ACCOUNT_BANS_FILE_NAME)
        if strings:
            pinylib.CONFIG.B_STRING_BANS = pinylib.file_handler.file_reader(self.config_path,
                                                                            pinylib.CONFIG.B_STRING_BANS_FILE_NAME)

    def has_level(self, level):
        """ 
        Checks the active user for correct user level.

        :param level: The level to check the active user against.
        :type level: int
        :return: True if the user has correct level, else False
        :rtype: bool
        """
        if self.active_user.user_level == 6:
            return False
        elif self.active_user.user_level <= level:
            return True
        return False

    @staticmethod
    def format_time(time_stamp, is_milli=False):
        """ 
        Converts a time stamp as seconds or milliseconds to (day(s)) hours minutes seconds.

        :param time_stamp: Seconds or milliseconds to convert.
        :param is_milli: The time stamp to format is in milliseconds.
        :return: A string in the format (days) hh:mm:ss
        :rtype: str
        """
        if is_milli:
            m, s = divmod(time_stamp / 1000, 60)
        else:
            m, s = divmod(time_stamp, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d == 0 and h == 0:
            human_time = '%02d:%02d' % (m, s)
        elif d == 0:
            human_time = '%d:%02d:%02d' % (h, m, s)
        else:
            human_time = '%d Day(s) %d:%02d:%02d' % (d, h, m, s)
        return human_time

    def check_msg(self, msg):
        """ 
        Checks the chat message for ban string.

        :param msg: The chat message.
        :type msg: str
        """
        should_be_banned = False
        chat_words = msg.split(' ')
        for bad in pinylib.CONFIG.B_STRING_BANS:
            if bad.startswith('*'):
                _ = bad.replace('*', '')
                if _ in msg:
                    should_be_banned = True
            elif bad in chat_words:
                    should_be_banned = True
        if should_be_banned:
            if pinylib.CONFIG.B_USE_KICK_AS_AUTOBAN:
                self.send_kick_msg(self.active_user.id)
            else:
                self.send_ban_msg(self.active_user.id)

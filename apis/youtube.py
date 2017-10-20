# -*- coding: utf-8 -*-
""" Contains functions to fetch info from youtube's API (googleapis.com/youtube/v3/) """
import logging

import util.web
import _track
from util import string_util


API_KEY = 'AIzaSyCPQe4gGZuyVQ78zdqf9O5iEyfVLPaRwZg'

ALLOWED_COUNTRIES = ['DK', 'PL', 'UK']

REFERER = 'https://tinychat.com'

SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search?' \
             'type=video&key={0}&maxResults=50&q={1}&part=snippet'

PLAYLIST_SEARCH_URL = 'https://www.googleapis.com/youtube/v3/search?' \
                      'type=playlist&key={0}&maxResults=50&q={1}&part=snippet'

PLAYLIST_ITEMS_URL = 'https://www.googleapis.com/youtube/v3/playlistItems?' \
                     'key={0}&playlistId={1}&maxResults=50&part=snippet,id'

VIDEO_DETAILS_URL = 'https://www.googleapis.com/youtube/v3/videos?' \
                    'id={1}&key={0}&part=contentDetails,snippet'


log = logging.getLogger(__name__)


def search(search_term):
    """
    Searches the youtube API for a youtube video matching the search term.

    A json response of ~50 possible items matching the search term will be presented.
    Each video_id will then be checked by video_details() until a candidate has been found
    and the resulting Track can be returned.

    :param search_term: The search term str to search for.
    :type search_term: str
    :return: A Track object or None on error.
    :rtype: Track | None
    """
    url = SEARCH_URL.format(API_KEY, util.web.quote(search_term.encode('ascii', 'ignore')))
    response = util.web.http_get(url=url, json=True, referer=REFERER)

    _error = None
    if response['json'] is not None:
        track = None
        if 'items' in response['json']:

            try:
                for item in response['json']['items']:
                    video_id = item['id']['videoId']
                    details = video_details(video_id)

                    if details is not None:
                        track = details
                        break

            except KeyError as ke:
                _error = ke
            finally:
                if _error is not None:
                    log.error(_error)
                    return None

        return track


def search_list(search_term, results=10):
    """
    Searches the API of youtube for videos matching the search term.

    Instead of returning only one video matching the search term, we return a list of candidates.

    :param search_term: The search term to search for.
    :type search_term: str
    :param results: Amount of items in the list.
    :type results: int
    :return: A list of Track objects or None on error.
    :rtype: list | None
    """
    url = SEARCH_URL.format(API_KEY, util.web.quote(search_term.encode('ascii', 'ignore')))
    response = util.web.http_get(url=url, json=True, referer=REFERER)

    _error = None
    if response['json'] is not None:
        track_list = []
        if 'items' in response['json']:

            try:
                for i, item in enumerate(response['json']['items']):
                    if i == results:
                        return track_list
                    else:
                        video_id = item['id']['videoId']
                        track = video_details(video_id)

                        if track is not None:
                            track_list.append(track)

            except KeyError as ke:
                _error = ke
            finally:
                if _error is not None:
                    log.error(_error)
                    return None

        return track_list


def playlist_search(search_term, results=5):
    """
    Searches youtube for a playlist matching the search term.

    :param search_term: The search term to search to search for.
    :type search_term: str
    :param results: the number of playlist matches we want returned.
    :type results: int
    :return: A list of dictionaries with the keys: ´playlist_title´, ´playlist_id´
    :rtype: list | None
    """
    url = PLAYLIST_SEARCH_URL.format(API_KEY, util.web.quote(search_term.encode('ascii', 'ignore')))
    response = util.web.http_get(url=url, json=True, referer=REFERER)

    _error = None
    if response['json'] is not None:
        play_lists = []
        if 'items' in response['json']:

            try:
                for i, item in enumerate(response['json']['items']):
                    if i == results:
                        return play_lists

                    playlist_id = item['id']['playlistId']
                    playlist_title = item['snippet']['title']  #
                    play_list_info = {
                        'playlist_title': playlist_title,
                        'playlist_id': playlist_id
                    }
                    play_lists.append(play_list_info)
            except KeyError as ke:
                _error = ke
            finally:
                if _error is not None:
                    log.error(_error)
                    return None

        return play_lists


def playlist_videos(playlist_id):
    """
    Find the videos for a given playlist ID.

    The list returned will contain a maximum of 50 videos.

    :param playlist_id: The playlist ID
    :type playlist_id: str
    :return: A list ofTrack objects.
    :rtype: list | None
    """
    url = PLAYLIST_ITEMS_URL.format(API_KEY, playlist_id)
    response = util.web.http_get(url=url, json=True, referer=REFERER)

    _error = None
    if response['json'] is not None:
        video_list = []

        # next_page_token = response['json']['nextPageToken']
        if 'items' in response['json']:

            try:
                for item in response['json']['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    track = video_details(video_id)

                    if track is not None:
                        video_list.append(track)
            except KeyError as ke:
                _error = ke
            finally:
                if _error is not None:
                    log.error(_error)
                    return None

        return video_list


def video_details(video_id, check=True):
    """
    Youtube helper function to get the video time for a given video id.

    Checks a youtube video id to see if the video is blocked or allowed
    in the ALLOWED_COUNTRIES list. If a video is blocked in one of the countries, 
    None is returned. If a video is NOT allowed in ONE of the countries, 
    None is returned else a Track object will be returned.

    :param video_id: The youtube video id to check.
    :type video_id: str
    :param check: check for region restriction. Default: True
    :type check: bool
    :return: A Track object.
    :rtype: Track | None
    """
    url = VIDEO_DETAILS_URL.format(API_KEY, video_id)
    response = util.web.http_get(url=url, json=True, referer=REFERER)

    _error = None
    if response['json'] is not None:
        if 'items' in response['json']:
            track = None
            if len(response['json']['items']) != 0:

                try:
                    content_details = response['json']['items'][0]['contentDetails']
                    if check:
                        if 'regionRestriction' in content_details:

                            if 'blocked' in content_details['regionRestriction']:
                                blocked = content_details['regionRestriction']['blocked']
                                if [i for e in ALLOWED_COUNTRIES for i in blocked if e in i]:
                                    log.info('%s is blocked in: %s' % (video_id, blocked))
                                    return None

                            if 'allowed' in content_details['regionRestriction']:
                                allowed = content_details['regionRestriction']['allowed']
                                if [i for e in ALLOWED_COUNTRIES for i in allowed if e not in i]:
                                    log.info('%s is allowed in: %s' % (video_id, allowed))
                                    return None

                    video_time = string_util.convert_to_seconds(content_details['duration'])
                    video_title = response['json']['items'][0]['snippet']['title']
                    image_medium = response['json']['items'][0]['snippet']['thumbnails']['medium']['url']

                    track = _track.Track(video_id=video_id, video_time=video_time, video_title=video_title,
                                         image=image_medium)

                except KeyError as ke:
                    _error = ke
                finally:
                    if _error is not None:
                        log.error(_error)
                        return None

            return track

# -*- coding: utf-8 -*-
"""Kodi library integration"""
from __future__ import unicode_literals

import os
import codecs
from datetime import datetime, timedelta

import xbmc

import resources.lib.common as common
import resources.lib.cache as cache
import resources.lib.api.shakti as api

FILE_PROPS = [
    'title', 'genre', 'year', 'rating', 'duration', 'playcount', 'director',
    'tagline', 'plot', 'plotoutline', 'originaltitle', 'writer', 'studio',
    'mpaa', 'cast', 'country', 'runtime', 'set', 'showlink', 'season',
    'episode', 'showtitle', 'file', 'resume', 'tvshowid', 'setid', 'tag',
    'art', 'uniqueid']

LIBRARY_HOME = 'library'
FOLDER_MOVIES = 'movies'
FOLDER_TV = 'shows'

__LIBRARY__ = None


class ItemNotFound(Exception):
    """The requested item could not be found in the Kodi library"""
    pass


def _library():
    # pylint: disable=global-statement
    global __LIBRARY__
    if not __LIBRARY__:
        try:
            __LIBRARY__ = cache.get(cache.CACHE_LIBRARY, 'library')
        except cache.CacheMiss:
            __LIBRARY__ = {}
    return __LIBRARY__


def library_path():
    """Return the full path to the library"""
    return (common.ADDON.getSetting('customlibraryfolder')
            if common.ADDON.getSettingBool('enablelibraryfolder')
            else common.DATA_PATH)


def save_library():
    """Save the library to disk via cache"""
    if __LIBRARY__ is not None:
        cache.add(cache.CACHE_LIBRARY, 'library', __LIBRARY__,
                  ttl=cache.TTL_INFINITE, to_disk=True)


def get_item(videoid, include_props=False):
    """Find an item in the Kodi library by its Netflix videoid and return
    Kodi DBID and mediatype"""
    try:
        filepath = common.get_path(videoid.to_list(), _library())['file']
        params = {'file': filepath, 'media': 'video'}
        if include_props:
            params['properties'] = FILE_PROPS
        return common.json_rpc('Files.GetFileDetails', params)['filedetails']
    except:
        raise ItemNotFound(
            'The video with id {} is not present in the Kodi library'
            .format(videoid))


def is_in_library(videoid):
    """Return True if the video is in the local Kodi library, else False"""
    return common.get_path_safe(videoid.to_list(), _library()) is not None


def compile_tasks(videoid):
    """Compile a list of tasks for items based on the videoid"""
    metadata = api.metadata(videoid)
    if videoid.mediatype == common.VideoId.MOVIE:
        return _create_movie_task(videoid, metadata)
    elif videoid.mediatype in common.VideoId.TV_TYPES:
        return _create_tv_tasks(videoid, metadata)

    raise ValueError('Cannot handle {}'.format(videoid))


def _create_movie_task(videoid, metadata):
    """Create a task for a movie"""
    name = '{title} ({year})'.format(
        title=metadata['title'],
        year=metadata['year'])
    return [_create_item_task(name, FOLDER_MOVIES, videoid, name, name)]


def _create_tv_tasks(videoid, metadata):
    """Create tasks for a show, season or episode.
    If videoid represents a show or season, tasks will be generated for
    all contained seasons and episodes"""
    if videoid.mediatype == common.VideoId.SHOW:
        return _compile_show_tasks(videoid, metadata)
    elif videoid.mediatype == common.VideoId.SEASON:
        return _compile_season_tasks(
            videoid, metadata, common.find_season(videoid.seasonid,
                                                  metadata))
    return [_create_episode_task(videoid, metadata)]


def _compile_show_tasks(videoid, metadata):
    """Compile a list of task items for all episodes of all seasons
    of a tvshow"""
    # This nested comprehension is nasty but neccessary. It flattens
    # the task lists for each season into one list
    return [task for season in metadata['seasons']
            for task in _compile_season_tasks(
                videoid.derive_season(season['id']), metadata, season)]


def _compile_season_tasks(videoid, metadata, season):
    """Compile a list of task items for all episodes in a season"""
    return [_create_episode_task(videoid.derive_episode(episode['id']),
                                 metadata, season, episode)
            for episode in season['episodes']]


def _create_episode_task(videoid, metadata, season=None, episode=None):
    """Export a single episode to the library"""
    showname = metadata['title']
    season = season or common.find_season(
        videoid.seasonid, metadata['seasons'])
    episode = episode or common.find_episode(
        videoid.episodeid, metadata['seasons'])
    title = episode['title']
    filename = 'S{:02d}E{:02d}'.format(season['seq'], episode['seq'])
    title = ' - '.join((showname, filename, title))
    return _create_item_task(title, FOLDER_TV, videoid, showname, filename)


def _create_item_task(title, section, videoid, destination, filename):
    """Create a single task item"""
    return {
        'title': title,
        'section': section,
        'videoid': videoid,
        'destination': destination,
        'filename': filename
    }


def export_item(item_task, library_home):
    """Create strm file for an item and add it to the library"""
    destination_folder = os.path.join(
        library_home, item_task['section'], item_task['destination'])
    export_filename = os.path.join(
        destination_folder, item_task['filename'] + '.strm')
    _create_destination_folder(destination_folder)
    _write_strm_file(item_task, export_filename)
    _add_to_library(item_task['videoid'], export_filename)


def _create_destination_folder(destination_folder):
    """Create destination folder, ignore error if it already exists"""
    try:
        os.makedirs(xbmc.translatePath(destination_folder))
    except OSError as exc:
        if exc.errno != os.errno.EEXIST:
            raise


def _write_strm_file(item_task, export_filename):
    """Write the playable URL to a strm file"""
    try:
        with codecs.open(xbmc.translatePath(export_filename),
                         mode='w',
                         encoding='utf-8',
                         errors='replace') as filehandle:
            filehandle.write(
                common.build_url(videoid=item_task['videoid'],
                                 mode=common.MODE_PLAY))
    except OSError as exc:
        if exc.errno == os.errno.EEXIST:
            common.info('{} already exists, skipping export'
                        .format(export_filename))
        else:
            raise


def _add_to_library(videoid, export_filename):
    """Add an exported file to the library"""
    library_node = _library()
    for id_item in videoid.to_list():
        if id_item not in library_node:
            library_node[id_item] = {}
        library_node = library_node[id_item]
    library_node['file'] = export_filename
    save_library()


def remove_item(item_task):
    """Remove an item from the library and delete if from disk"""
    id_path = item_task['videoid'].to_list()
    exported_filename = xbmc.translatePath(
        common.get_path(id_path, _library())['file'])
    parent_folder = os.path.dirname(exported_filename)
    os.remove(xbmc.translatePath(exported_filename))
    if not os.listdir(parent_folder):
        os.remove(parent_folder)
    common.remove_path(id_path, _library())
    save_library()


def update_item(item_task, library_home):
    """Remove and then re-export an item to the Kodi library"""
    remove_item(item_task)
    export_item(item_task, library_home)


def _update_running():
    update = common.ADDON.getSetting('update_running') or None
    if update:
        starttime = common.strp(update, '%Y-%m-%d %H:%M')
        if (starttime + timedelta(hours=6)) <= datetime.now():
            common.ADDON.setSetting('update_running', 'false')
            common.warn('Canceling previous library update: duration >6 hours')
        else:
            common.debug('DB Update already running')
            return True
    return False


def update_library():
    """
    Update the local Kodi library with new episodes of exported shows
    """
    if not _update_running():
        common.info('Triggering library update')
        xbmc.executebuiltin(
            ('XBMC.RunPlugin(plugin://{}/?action=export-new-episodes'
             '&inbackground=True)')
            .format(common.ADDON_ID))

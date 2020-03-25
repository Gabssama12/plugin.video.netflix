# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017 Sebastian Golasch (plugin.video.netflix)
    Copyright (C) 2019 Stefano Gottardo - @CastagnaIT (original implementation module)
    Defines upgrade actions to the frontend and backend, to be performed by upgrade_controller

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
from __future__ import absolute_import, division, unicode_literals

import os

import xbmc
import xbmcvfs

from resources.lib.common import delete_folder_contents, debug, error
from resources.lib.globals import g


def delete_cache_folder():
    # Delete cache folder in the add-on userdata (no more needed with the new cache management)
    debug('Deleting the cache folder from add-on userdata folder')
    try:
        delete_folder_contents(os.path.join(g.DATA_PATH, 'cache'), True)
        xbmc.sleep(80)
        xbmcvfs.rmdir(os.path.join(g.DATA_PATH, 'cache'))
    except Exception:  # pylint: disable=broad-except
        import traceback
        error(traceback.format_exc())

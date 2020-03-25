# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017 Sebastian Golasch (plugin.video.netflix)
    Copyright (C) 2020 Stefano Gottardo (original implementation module)
    Caching facilities. Caches are segmented into buckets.
    Within each bucket, identifiers for cache entries must be unique.

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
from __future__ import absolute_import, division, unicode_literals

from resources.lib.common import make_http_call_cache
from resources.lib.globals import g

try:
    import cPickle as pickle
except ImportError:
    import pickle


class Cache(object):
    """Cache"""

    # All the cache remains in memory until the service will be stopped

    # The persistent cache option:
    # This option will enable to save/read the cache data in a database (see cache_management.py)
    # When a cache bucket is set as 'persistent', allow to the cache data to survive events that stop the netflix
    # service for example: update of add-on, restart of Kodi or change Kodi profile.
    # This option can be enabled for each individual bucket,
    # by set 'is_persistent' to True in the bucket variable (see cache_utils.py)

    def get(self, bucket, identifier):
        """Get a item from cache bucket"""
        call_args = {
            'bucket': bucket,
            'identifier': str(identifier)
        }
        data = _make_call('get', call_args)
        return _deserialize_data(data)

    def add(self, bucket, identifier, data, ttl=None, expires=None):
        """
        Add or update an item to a cache bucket

        :param bucket: bucket where save the data
        :param identifier: key identifier of the data
        :param data: the content
        :param ttl: override default expiration (in seconds)
        :param expires: override default expiration (in timestamp) if specified override also the 'ttl' value
        """
        call_args = {
            'bucket': bucket,
            'identifier': str(identifier),
            'data': None,  # This value is injected after the _make_call
            'ttl': ttl,
            'expires': expires
        }
        _make_call('add', call_args, _serialize_data(data))

    def delete(self, bucket, identifier):
        """Delete an item from cache bucket"""
        call_args = {
            'bucket': bucket,
            'identifier': str(identifier)
        }
        _make_call('delete', call_args)

    def clear(self, buckets=None, clear_database=True):
        """
        Clear the cache

        :param buckets: list of buckets to clear, if not specified clear all the cache
        :param clear_database: if True clear also the database data
        """
        call_args = {
            'buckets': buckets,
            'clear_database': clear_database
        }
        _make_call('clear', call_args)


def _make_call(callname, params=None, data=None):
    if g.IS_SERVICE:
        if 'data' in params:
            params['data'] = data
        # In the service instance direct call to cache management
        func = getattr(g.CACHE_MANAGEMENT, callname)
        return func(**params)
    # In the client-frontend instance is needed to use the IPC cache http service
    return make_http_call_cache(callname, params, data)


def _serialize_data(value):
    if g.PY_IS_VER2:
        # On python 2 pickle.dumps produces str
        # Pickle on python 2 use non-standard byte-string seem not possible convert it in to byte in a easy way
        # then serialize it with base64
        from base64 import standard_b64encode
        return standard_b64encode(pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL))
    # On python 3 pickle.dumps produces byte
    return pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)


def _deserialize_data(value):
    if g.PY_IS_VER2:
        # On python 2 pickle.loads wants str
        from base64 import standard_b64decode
        return pickle.loads(standard_b64decode(value))
    # On python 3 pickle.loads wants byte
    return pickle.loads(value)

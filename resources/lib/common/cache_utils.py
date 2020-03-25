# -*- coding: utf-8 -*-
"""
    Copyright (C) 2017 Sebastian Golasch (plugin.video.netflix)
    Copyright (C) 2020 Stefano Gottardo (original implementation module)
    Common base for cache classes

    SPDX-License-Identifier: MIT
    See LICENSES/MIT.md for more information.
"""
from __future__ import absolute_import, division, unicode_literals

from functools import wraps

from resources.lib.api.exceptions import CacheMiss
from resources.lib.globals import g

# Cache buckets
CACHE_COMMON = {'name': 'cache_common', 'is_persistent': False, 'default_ttl': g.CACHE_TTL}
CACHE_GENRES = {'name': 'cache_genres', 'is_persistent': False, 'default_ttl': g.CACHE_TTL}
CACHE_SUPPLEMENTAL = {'name': 'cache_supplemental', 'is_persistent': False, 'default_ttl': g.CACHE_TTL}
CACHE_METADATA = {'name': 'cache_metadata', 'is_persistent': True, 'default_ttl': g.CACHE_METADATA_TTL}
CACHE_INFOLABELS = {'name': 'cache_infolabels', 'is_persistent': True, 'default_ttl': g.CACHE_METADATA_TTL}
CACHE_ARTINFO = {'name': 'cache_artinfo', 'is_persistent': True, 'default_ttl': g.CACHE_METADATA_TTL}
CACHE_MANIFESTS = {'name': 'cache_manifests', 'is_persistent': False, 'default_ttl': g.CACHE_TTL}
CACHE_BOOKMARKS = {'name': 'cache_bookmarks', 'is_persistent': False, 'default_ttl': g.CACHE_TTL}

# The complete list of buckets (to obtain the list quickly)
BUCKET_NAMES = ['cache_common', 'cache_genres', 'cache_supplemental', 'cache_metadata',
                'cache_infolabels', 'cache_artinfo', 'cache_manifests', 'cache_bookmarks']

BUCKETS = [CACHE_COMMON, CACHE_GENRES, CACHE_SUPPLEMENTAL, CACHE_METADATA, CACHE_INFOLABELS,
           CACHE_ARTINFO, CACHE_MANIFESTS, CACHE_BOOKMARKS]

# For my list we limit the ttl of max 2 hour, otherwise if the list it is modified by other devices
# will never update until ttl expire or will be used the forced manual update via context menu
CACHE_MYLIST_TTL_MAX = 7200


# Logic to get the identifier
# cache_output: called without params, use the first argument value of the function as identifier
# cache_output: with identify_from_kwarg_name, get value identifier from kwarg name specified,
#               if None value fallback to first function argument value

# identify_append_from_kwarg_name - if specified append the value after the kwarg identify_from
#                                  _kwarg_name, to creates a more specific identifier
# identify_fallback_arg_index - to change the default fallback arg index (0), where the identifier
#                               get the value from the func arguments
# fixed_identifier - note if specified all other params are ignored

def cache_output(bucket, fixed_identifier=None,
                 identify_from_kwarg_name='videoid',
                 identify_append_from_kwarg_name=None,
                 identify_fallback_arg_index=0,
                 ttl=None):
    """Decorator that ensures caching the output of a function"""
    # pylint: too-many-arguments
    def caching_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            ttl_override = None
            try:
                arg_value, identifier = _get_identifier(fixed_identifier,
                                                        identify_from_kwarg_name,
                                                        identify_append_from_kwarg_name,
                                                        identify_fallback_arg_index,
                                                        args,
                                                        kwargs)
                if ttl is None and arg_value == 'mylist':
                    ttl_override = min(g.CACHE_TTL, CACHE_MYLIST_TTL_MAX)
                if not identifier:
                    # Do not cache if identifier couldn't be determined
                    return func(*args, **kwargs)
                return g.CACHE.get(bucket, identifier)
            except CacheMiss:
                output = func(*args, **kwargs)
                g.CACHE.add(bucket, identifier, output, ttl=ttl or ttl_override)
                return output
        return wrapper
    return caching_decorator


def generate_identifier(partial_identifier):
    """Generate a cache identifier"""
    # The cache must be distinct by profile to avoid mix data
    return g.LOCAL_DB.get_active_profile_guid() + '_' + partial_identifier


def _get_identifier(fixed_identifier, identify_from_kwarg_name,
                    identify_append_from_kwarg_name, identify_fallback_arg_index, args, kwargs):
    """Return the identifier to use with the caching_decorator"""
    # common.debug('Get_identifier args: {}', args)
    # common.debug('Get_identifier kwargs: {}', kwargs)
    arg_value = None
    if fixed_identifier:
        identifier = fixed_identifier
    else:
        identifier = kwargs.get(identify_from_kwarg_name)
        if not identifier and args:
            arg_value = args[identify_fallback_arg_index]
            identifier = arg_value
        if identifier and identify_append_from_kwarg_name and \
           kwargs.get(identify_append_from_kwarg_name):
            identifier += '_' + kwargs.get(identify_append_from_kwarg_name)
    # common.debug('Get_identifier identifier value: {}', identifier if identifier else 'None')
    return arg_value, generate_identifier(str(identifier))

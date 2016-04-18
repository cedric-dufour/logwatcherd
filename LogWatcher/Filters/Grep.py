# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent

#
# Log Watcher Daemon (logwatcherd)
# Copyright (C) 2016 Cedric Dufour <http://cedric.dufour.name>
# Author: Cedric Dufour <http://cedric.dufour.name>
#
# The Log Watcher Daemon (logwatcherd) is free software: you can redistribute
# it and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, Version 3.
#
# The Log Watcher Daemon (logwatcherd) is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details.
#

#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
import re
import urlparse

# LogWatcher
from LogWatcher.Filters import Filter
from LogWatcher import Data


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Grep(Filter):
    """
    Regular-Expression Filter.

    This filter tests the provided data against the configured regular expression
    and outputs the data corresponding to the requested group.

    Configuration parameters are:
     - [MANDATORY] pattern=<string>: regular expression
     - [OPTIONAL]  ignorecase:       case-insensitive flag
     - [OPTIONAL]  group=<int>:      output data group (default: 0=the entire line)

    In addition, the following "magic snippets" can be used to match/output
    specific data:
     - '%{ip}':    IP address (IPv4 or IPv6)
     - '%{ipv4}':  IPv4 address
     - '%{ipv6}':  IPv6 address
     - '%{email}': e-mail address
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration):
        # Parent constructor
        Filter.__init__(self, _oWatcher, _sConfiguration)

        # Configuration
        dConfiguration = urlparse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... flags
        iFlags = 0
        if 'ignorecase' in dConfiguration_keys:
            iFlags |= re.IGNORECASE

        # ... regexp
        if 'pattern' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Filter:Grep(%s)]: Missing \'pattern\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'pattern\' configuration parameter')
        sPattern = dConfiguration['pattern'][0]
        sPattern = sPattern.replace('%{ip}', '([0-9]{1,3}(\.[0-9]{1,3}){3}|[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7})') \
            .replace('%{ipv4}', '[0-9]{1,3}(\.[0-9]{1,3}){3}') \
            .replace('%{ipv6}', '[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7}') \
            .replace('%{email}', '[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*@[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*\.[a-zA-Z]{2,}')
        try:
            self.__oRegExp = re.compile(sPattern, iFlags)
        except Exception:
            _oWatcher.log('ERROR[Filter:Grep(%s)]: Invalid \'pattern\' configuration parameter\n' % _oWatcher.name())
            raise

        # ... group
        self.__iGroup = 0
        if 'group' in dConfiguration_keys:
            try:
                self.__iGroup = int(dConfiguration['group'][0])
                if self.__iGroup<0:
                    raise ValueError('Value must me greater or equal to zero')
            except Exception:
                _oWatcher.log('ERROR[Filter:Grep(%s)]: Invalid \'group\' configuration parameter\n' % _oWatcher.name())
                raise


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def feed(self, _sData):
        # Test the data against the regular expression
        oMatch = self.__oRegExp.search(_sData)
        if oMatch is None:
            return None

        # Output the requested group
        return Data(self._oWatcher.name(), _sData, oMatch.group(self.__iGroup))

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
from LogWatcher.Conditioners import Conditioner
from LogWatcher import Data


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Sed(Conditioner):
    """
    Sed-like Conditioner.

    This conditioner returns the provided data depending on its (not) matching
    the configured regular expression and optionally replacing the output data.

    If no replacement data is specified, this conditioner does "If (not)":
    if the data does not match the configured pattern, None is returned
    (which will make the parent watcher stop further processing of the data).

    If replacement data is specified, this conditioner does "Find-and-Replace":
    if the data does not match the configured pattern, the passed data object is
    returned "as is"; if it does match, the configured replacement string is used
    to replace the filtered (output) data in the data object (matched group(s)
    can be inserted in the replacement string by using "\<int>" backreferences).

    Configuration parameters are:
     - [REQ] pattern=<string>
             Regular expression
     - [opt] ignorecase (flag)
             Case-insensitive match
     - [opt] not (flag)
             Invert match logic (logical not)
     - [opt] raw (flag)
             Test the producer (raw) data instead of the filter (output) data
     - [opt] replace=<string>
             Replacement data

    In addition, the following "magic snippets" can be used to match/output
    specific data:
     - '%{ip}':    IP address (IPv4 or IPv6)
     - '%{ipv4}':  IPv4 address
     - '%{ipv6}':  IPv6 address
     - '%{email}': e-mail address

    Example (watcher configuration):
     - conditioners = Sed?pattern=foo&replace=bar,
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration):
        # Parent constructor
        Conditioner.__init__(self, _oWatcher, _sConfiguration)

        # Configuration
        dConfiguration = urlparse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... flags
        iFlags = 0
        if 'ignorecase' in dConfiguration_keys:
            iFlags |= re.IGNORECASE

        # ... regexp
        if 'pattern' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Conditioner:Sed(%s)]: Missing \'pattern\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'pattern\' configuration parameter')
        sPattern = dConfiguration['pattern'][0]
        sPattern = sPattern.replace('%{ip}', '([0-9]{1,3}(\.[0-9]{1,3}){3}|[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7})') \
            .replace('%{ipv4}', '[0-9]{1,3}(\.[0-9]{1,3}){3}') \
            .replace('%{ipv6}', '[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7}') \
            .replace('%{email}', '[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*@[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*\.[a-zA-Z]{2,}')
        try:
            self.__oRegExp = re.compile(sPattern, iFlags)
        except Exception:
            _oWatcher.log('ERROR[Conditioner:Sed(%s)]: Invalid \'pattern\' configuration parameter\n' % _oWatcher.name())
            raise

        # ... logical not
        self.__bNot = False
        if 'not' in dConfiguration_keys:
            self.__bNot = True

        # ... raw data
        self.__bRaw = False
        if 'raw' in dConfiguration_keys:
            self.__bRaw = True

        # ... replace / group
        self.__sReplace = None
        self.__bExpand = False
        if 'replace' in dConfiguration_keys:
            self.__sReplace = dConfiguration['replace'][0]
            if not self.__bNot and re.match('(^|[^\\\\])\\\\[0-9]', self.__sReplace):
                self.__bExpand = True


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def feed(self, _oData):
        # Test the data against the regular expression
        oMatch = self.__oRegExp.search(_oData.data_raw if self.__bRaw else _oData.data)
        if (oMatch is None and not self.__bNot) or (oMatch is not None and self.__bNot):
            if self.__sReplace is not None:
                # Find-and-Replace
                return _oData
            else:
                # If (not)
                return None

        # Output
        if self.__sReplace is not None:
            return Data(_oData.watcher, _oData.data_raw, oMatch.expand(self.__sReplace) if self.__bExpand else self.__sReplace)
        else:
            return _oData

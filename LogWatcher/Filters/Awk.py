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

class Awk(Filter):
    """
    Awk-like Filter.

    This filter tests the requested input data field against the configured
    regular expression and outputs the requested output data field.

    Configuration parameters are:
     - [OPTIONAL]  separator=<string>: field separator (default: ,)
     - [MANDATORY] input=<int>:        input/filter data field (note: 0=the entire line)
     - [MANDATORY] pattern=<string>:   regular expression
     - [OPTIONAL]  ignorecase:         case-insensitive flag
     - [OPTIONAL]  output=<int>:       output data field (default: 0=the entire line)

    In addition, the following "magic snippets" can be used to match specific data:
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

        # ... separator
        self.__sFieldSeparator = ','
        if 'separator' in dConfiguration_keys:
            self.__sFieldSeparator = dConfiguration['separator'][0]

        # ... input
        if 'input' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Filter:Awk(%s)]: Missing \'input\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'input\' configuration parameter')
        try:
            self.__iFieldInput = int(dConfiguration['input'][0])
            if self.__iFieldInput<0:
                raise ValueError('Value must me greater or equal to zero')
        except Exception:
            _oWatcher.log('ERROR[Filter:Awk(%s)]: Invalid \'input\' configuration parameter\n' % _oWatcher.name())
            raise

        # ... output
        self.__iFieldOutput = 0
        if 'output' in dConfiguration_keys:
            try:
                self.__iFieldOutput = int(dConfiguration['output'][0])
                if self.__iFieldOutput<0:
                    raise ValueError('Value must me greater or equal to zero')
            except Exception:
                _oWatcher.log('ERROR[Filter:Awk(%s)]: Invalid \'output\' configuration parameter\n' % _oWatcher.name())
                raise

        # ... input/output check
        if self.__iFieldInput==0 and self.__iFieldOutput==0:
            _oWatcher.log('WARNING[Filter:Awk(%s)]: Matching/outputting the entire line would be faster with the Grep filter\n' % _oWatcher.name())


        # ... flags
        iFlags = 0
        if 'ignorecase' in dConfiguration_keys:
            iFlags |= re.IGNORECASE

        # ... regexp
        if 'pattern' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Filter:Awk(%s)]: Missing \'pattern\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'pattern\' configuration parameter')
        sPattern = dConfiguration['pattern'][0]
        sPattern = sPattern.replace('%{ip}', '([0-9]{1,3}(\.[0-9]{1,3}){3}|[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7})') \
            .replace('%{ipv4}', '[0-9]{1,3}(\.[0-9]{1,3}){3}') \
            .replace('%{ipv6}', '[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7}') \
            .replace('%{email}', '[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*@[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*\.[a-zA-Z]{2,}')
        try:
            self.__oRegExp = re.compile(sPattern, iFlags)
        except Exception:
            _oWatcher.log('ERROR[Filter:Awk(%s)]: Invalid \'pattern\' configuration parameter\n' % _oWatcher.name())
            raise


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def feed(self, _sData):
        # Split the data into fields
        lsFields = _sData.split(self.__sFieldSeparator)

        # Test the requested field against the regular expression
        oMatch = self.__oRegExp.search(_sData if self.__iFieldInput==0 else lsFields[self.__iFieldInput-1])
        if oMatch is None:
            return None

        # Output the requested field
        return Data(self._oWatcher.name(), _sData, _sData if self.__iFieldOutput==0 else lsFields[self.__iFieldOutput-1])

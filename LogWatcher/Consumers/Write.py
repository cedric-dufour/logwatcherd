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
import urlparse

# LogWatcher
from LogWatcher.Consumers import Consumer


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Write(Consumer):
    """
    File Writer Consumer.

    This consumer writes the provided data to the given file.

    Configuration parameters are:
     - [MANDATORY] file=<string>:   file path
     - [OPTIONAL]  truncate:        file truncate flag
     - [OPTIONAL]  exclusive:       exclusive access flag
     - [OPTIONAL]  prefix=<string>: prefix data written to file
     - [OPTIONAL]  suffix=<string>: suffix data written to file
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration):
        # Parent constructor
        Consumer.__init__(self, _oWatcher, _sConfiguration)

        # Configuration
        dConfiguration = urlparse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... flags
        self.__bTruncate = False
        if 'truncate' in dConfiguration_keys:
            self.__bTruncate = True
        self.__bExclusive = False
        if 'exclusive' in dConfiguration_keys:
            self.__bExclusive = True

        # ... file
        if 'file' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Consumer:Write(%s)]: Missing \'file\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'file\' configuration parameter')
        self.__sFile = dConfiguration['file'][0]

        # ... prefix
        self.__sPrefix = ''
        if 'prefix' in dConfiguration_keys:
            self.__sPrefix = dConfiguration['prefix'][0]

        # ... suffix
        self.__sSuffix = ''
        if 'suffix' in dConfiguration_keys:
            self.__sSuffix = dConfiguration['suffix'][0]

        # File
        self.__oFile = None
        if self.__bExclusive:
            self.__oFile = open(self.__sFile, 'w' if self.__bTruncate else 'a')


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def feed(self, _oData):
        # Write the data to file
        sData = '%s%s%s\n' % (self.__sPrefix, _oData.data, self.__sSuffix)
        if self._bDebug:
            self._oWatcher.log('DEBUG[Consumer:Write(%s)]: Consumed data\n%s' % (self._oWatcher.name(), sData))
        if self.__oFile is None:
            with open(self.__sFile, 'w' if self.__bTruncate else 'a') as oFile:
                oFile.write(sData)
        else:
            self.__oFile.write(sData)
            self.__oFile.flush()

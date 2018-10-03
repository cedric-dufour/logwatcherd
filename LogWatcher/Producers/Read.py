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
import time
import urllib.parse

# LogWatcher
from LogWatcher.Producers import Producer


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Read(Producer):
    """
    File Reader Producer.

    This producer reads the configured file and feeds it to its parent watcher
    line by line.

    It is useful mostly for debugging purposes.

    Configuration parameters are:
     - [REQ] file=<string>
             File path
     - [opt] delay=<float> (default: 0.0)
             Delay between lines feed, in seconds

    Example (watcher configuration):
     - producer = Read?file=/var/log/syslog&delay=1
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration, _bSynchronous, _bBlocking, _fTimeout):
        # Parent constructor
        Producer.__init__(self, _oWatcher, _sConfiguration, _bSynchronous, _bBlocking, _fTimeout)

        # Configuration
        dConfiguration = urllib.parse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... file
        if 'file' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Producer:Read(%s)]: Missing \'file\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'file\' configuration parameter')
        self.__sFile = dConfiguration['file'][0]

        # ... delay
        self.__fDelay = None
        if 'delay' in dConfiguration_keys:
            try:
                self.__fDelay = float(dConfiguration['delay'][0])
                if self.__fDelay<0.0:
                    raise ValueError('Value must me greater or equal to zero')
            except Exception:
                _oWatcher.log('ERROR[Producer:Read(%s)]: Invalid \'delay\' configuration parameter\n' % _oWatcher.name())
                raise


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def run(self):
        # Feed the file content line-by-line
        with open(self.__sFile) as oFile:
            for sLine in oFile:
                if self._bStop: break
                self._feed(sLine.strip())
                if self.__fDelay is not None:
                    time.sleep(self.__fDelay)

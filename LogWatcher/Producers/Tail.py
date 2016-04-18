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
import os
import time
import urlparse

# LogWatcher
from LogWatcher.Producers import Producer


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Tail(Producer):
    """
    File "Tail" Producer (similar to UNIX 'tail -F ...').

    This producer watchs the given file and feeds new lines to its parent watcher
    as they appear.

    Configuration parameters are:
     - [MANDATORY] file=<string>:    file path
     - [OPTIONAL]  interval=<float>: file check interval, in seconds (default: 1.0)
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration, _bSynchronous, _bBlocking, _fTimeout):
        # Parent constructor
        Producer.__init__(self, _oWatcher, _sConfiguration, _bSynchronous, _bBlocking, _fTimeout)

        # Configuration
        dConfiguration = urlparse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... file
        if 'file' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Producer:Tail(%s)]: Missing \'file\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'file\' configuration parameter')
        self.__sFile = dConfiguration['file'][0]

        # ... interval
        self.__fInterval = 1.0
        if 'interval' in dConfiguration_keys:
            try:
                self.__fInterval = float(dConfiguration['interval'][0])
                if self.__fInterval<=0.0:
                    raise ValueError('Value must me greater than zero')
            except Exception:
                _oWatcher.log('ERROR[Producer:Tail(%s)]: Invalid \'interval\' configuration parameter\n' % _oWatcher.name())
                raise


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def run(self):
        # Feed the file content line-by-line
        bStarting = True
        while True:
            if self._bStop: break

            # Open file
            try:
                oFile = open(self.__sFile)
                oStat = os.stat(oFile.name)
                sFileID = '%s:%s' % (oStat.st_dev, oStat.st_ino) if os.name=='posix' else '%s' % oStat.st_ctime
            except (IOError, OSError):
                self._oWatcher.log('WARNING[Producer:Tail(%s)]: Failed to open file (%s); trying again...\n' % (self._oWatcher.name(), self.__sFile))
                time.sleep(5.0)
                continue

            with oFile:
                # Skip existing content
                if bStarting:
                    oFile.seek(0, os.SEEK_END)
                    bStarting = False

                while True:
                    # Get new lines
                    if self._bStop: break
                    iWhere = oFile.tell()
                    lsLines = oFile.readlines()
                    if lsLines:
                        for sLine in lsLines:
                            self._feed(sLine.strip())
                    else:
                        oFile.seek(iWhere)

                    # Wait for new lines
                    time.sleep(self.__fInterval)

                    # Check file hasn't been replaced (e.g. log rotation)
                    try:
                        oStat = os.stat(oFile.name)
                        sFileID_check = '%s:%s' % (oStat.st_dev, oStat.st_ino) if os.name=='posix' else '%s' % oStat.st_ctime
                        if sFileID_check != sFileID:
                            self._oWatcher.log('INFO[Producer:Tail(%s)]: File has been rotated; opening new one\n' % self._oWatcher.name())
                            break
                    except OSError:
                        self._oWatcher.log('INFO[Producer:Tail(%s)]: File has vanished; waiting for new one...\n' % self._oWatcher.name())
                        time.sleep(5.0)
                        break

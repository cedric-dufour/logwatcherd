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
# CLASSES
#------------------------------------------------------------------------------

class Logger:
    """
    Log Watcher Logger.

    This class is used to redirect the standard log output (sys.stdout or
    sys.stderr) to another destination; e.g. syslog.

    A logging function must be passed to it at instantiation time. This function
    is responsible to feed each log line to the proper destination.

    Once instantiated, the logger object is "activated" by re-defining the
    required output; e.g. sys.stderr = Logger(myLoggingFunction)
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _fnLog):
        # Fields
        self.__fnLog = _fnLog
        self.__sBuffer = ''


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def flush(self):
        if self.__sBuffer:
            self.__fnLog(self.__sBuffer)
            self.__sBuffer = ''


    def write(self, _s):
        while _s:
            i = _s.find('\n')
            if i < 0:
                self.__sBuffer += _s
                break
            self.__sBuffer += _s[:i]
            if self.__sBuffer:
                self.__fnLog(self.__sBuffer)
                self.__sBuffer = ''
            _s = _s[i+1:]


    def writelines(self, _lsLines):
        for sLine in _lsLines:
            self.write(sLine)

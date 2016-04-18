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

class Data:
    """
    Log Watcher Data.

    This class/object encapsulates log data and metadata, namely:
     - the originating watcher name (self.watcher)
     - the producer (raw) data (self.data_raw)
     - the filter (output) data (self.data)
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _sWatcher, _sDataRaw, _sData):
        """
        Constructor.

        @param  string  _sWatcher  Originating watcher name
        @param  string  _sDataRaw  Producer (raw) data
        @param  string  _sData     Filter (output) data
        """

        # Fields
        self.watcher = _sWatcher
        self.data_raw = _sDataRaw
        self.data = _sData

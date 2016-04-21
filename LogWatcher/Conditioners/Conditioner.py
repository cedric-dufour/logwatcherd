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

# LogWatcher
from LogWatcher import Plugin, Data


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Conditioner(Plugin):
    """
    Log Data Conditioner.

    This class is to be inherited by actual conditioners and describes the methods
    expected to be overriden.
    """

    #------------------------------------------------------------------------------
    # METHODS - TO BE OVERRIDDEN
    #------------------------------------------------------------------------------

    def feed(self, _oData):
        """
        Condition data (object) output by the filter or a previous conditioner.

        To interrupt the data processing, a conditioner must return None.
        Otherwise, a conditioner may alter the data object anyway it deems fit.

        The default implementation is to pass data through.

        @param  Data  _oData  Filtered or conditioned data object

        @return Data  Data object
        """

        # Data
        # (this is where your actual conditioner business ought to be implemented)
        return _oData

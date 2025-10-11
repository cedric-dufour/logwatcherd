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

from typing import TYPE_CHECKING

from ..Plugin import Plugin


if TYPE_CHECKING:
    from ..Data import Data


class Consumer(Plugin):
    """Log Data Consumer.

    This class is to be inherited by actual consumers and describes the methods
    expected to be overriden.
    """

    ############################################################################
    # METHODS - TO BE OVERRIDDEN
    ############################################################################

    def feed(self, _oData: "Data"):
        """Process data (object) output by the filter.

        The default implementation is to do nothing (exit immediately).

        Args:
            _oData: Filtered data (object)
        """
        # Action
        # (this is where your actual consumer business ought to be implemented)
        pass

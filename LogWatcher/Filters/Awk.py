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

import re
import urllib.parse
from typing import TYPE_CHECKING

from ..Data import Data
from .Filter import Filter


if TYPE_CHECKING:
    from ..Watcher import Watcher


class Awk(Filter):
    """Awk-like Filter.

    This filter tests the configured input data field against the configured
    regular expression and outputs the configured output data field.

    Configuration parameters are:
     - [opt] separator=<string> (default: ',')
             Field separator
     - [REQ] input=<int>
             Input/filter data field (0=the entire line)
     - [REQ] pattern=<string>
             Regular expression
     - [opt] ignorecase (flag)
             Case-insensitive match
     - [opt] output=<int> (default: 0)
             Output data field (0=the entire line)

    In addition, the following "magic snippets" can be used to match specific data:
     - '%{ip}':    IP address (IPv4 or IPv6)
     - '%{ipv4}':  IPv4 address
     - '%{ipv6}':  IPv6 address
     - '%{email}': e-mail address

    Example (watcher configuration):
     - filters = Awk?input=1&pattern=error&output=1,
    """

    ############################################################################
    # CONSTRUCTORS / DESTRUCTOR
    ############################################################################

    def __init__(self, _oWatcher: "Watcher", _sConfiguration):  # noqa: D107
        # Parent constructor
        Filter.__init__(self, _oWatcher, _sConfiguration)

        # Configuration
        dConfiguration = urllib.parse.parse_qs(_sConfiguration, keep_blank_values=True)

        # ... separator
        self.__sFieldSeparator = ","
        if "separator" in dConfiguration:
            self.__sFieldSeparator = dConfiguration["separator"][0]

        # ... input
        if "input" not in dConfiguration:
            _oWatcher.log("ERROR[Filter:Awk(%s)]: Missing 'input' configuration parameter\n" % _oWatcher.name())
            raise RuntimeError("Missing 'input' configuration parameter")
        try:
            self.__iFieldInput = int(dConfiguration["input"][0])
            if self.__iFieldInput < 0:
                raise ValueError("Value must me greater or equal to zero")
        except Exception:
            _oWatcher.log("ERROR[Filter:Awk(%s)]: Invalid 'input' configuration parameter\n" % _oWatcher.name())
            raise

        # ... output
        self.__iFieldOutput = 0
        if "output" in dConfiguration:
            try:
                self.__iFieldOutput = int(dConfiguration["output"][0])
                if self.__iFieldOutput < 0:
                    raise ValueError("Value must me greater or equal to zero")
            except Exception:
                _oWatcher.log("ERROR[Filter:Awk(%s)]: Invalid 'output' configuration parameter\n" % _oWatcher.name())
                raise

        # ... input/output check
        if self.__iFieldInput == 0 and self.__iFieldOutput == 0:
            _oWatcher.log(
                "WARNING[Filter:Awk(%s)]: Matching/outputting the entire line would be faster with the Grep filter\n"
                % _oWatcher.name()
            )

        # ... flags
        iFlags = 0
        if "ignorecase" in dConfiguration:
            iFlags |= re.IGNORECASE

        # ... regexp
        if "pattern" not in dConfiguration:
            _oWatcher.log("ERROR[Filter:Awk(%s)]: Missing 'pattern' configuration parameter\n" % _oWatcher.name())
            raise RuntimeError("Missing 'pattern' configuration parameter")
        sPattern = dConfiguration["pattern"][0]
        sPattern = (
            sPattern.replace("%{ip}", r"([0-9]{1,3}(\.[0-9]{1,3}){3}|[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7})")
            .replace("%{ipv4}", r"[0-9]{1,3}(\.[0-9]{1,3}){3}")
            .replace("%{ipv6}", r"[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7}")
            .replace(
                "%{email}",
                r"[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*@[-_a-zA-Z0-9]{1,}(\.[-_a-zA-Z0-9]{1,})*\.[a-zA-Z]{2,}",
            )
        )
        try:
            self.__oRegExp = re.compile(sPattern, iFlags)
        except Exception:
            _oWatcher.log("ERROR[Filter:Awk(%s)]: Invalid 'pattern' configuration parameter\n" % _oWatcher.name())
            raise

    ############################################################################
    # METHODS
    ############################################################################

    def feed(self, _sData: str) -> "Data":  # noqa: D102
        # Split the data into fields
        lsFields = _sData.split(self.__sFieldSeparator)

        # Test the requested field against the regular expression
        try:
            oMatch = self.__oRegExp.search(_sData if self.__iFieldInput == 0 else lsFields[self.__iFieldInput - 1])
        except IndexError:
            return None
        if oMatch is None:
            return None

        # Output the requested field
        return Data(
            self._oWatcher.name(), _sData, _sData if self.__iFieldOutput == 0 else lsFields[self.__iFieldOutput - 1]
        )

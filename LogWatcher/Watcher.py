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

import os
import traceback
from typing import TYPE_CHECKING

from .Conditioners.Conditioner import Conditioner
from .Consumers.Consumer import Consumer
from .Data import Data
from .Filters.Filter import Filter
from .Producers.Producer import Producer


if TYPE_CHECKING:
    from .Daemon import Daemon


class Watcher:
    """Log Watcher.

    This class/object correspond to a configured log watcher entity and gathers:
     - one producer
     - zero-to-many filters
     - one-to-many consumers

    Once started, the watcher will in turn start the producer, which will feed its
    output back to it.
    Each output is then fed to the configured filters, each in turn.
    The first matching filter will then return a fully populated data object.
    That data object is then fed to the conditioners, each in turn.
    If a conditioner returns no data (None), further processing is interrupted.
    Otherwise, the resulting data object is eventually fed to the consumers.
    """

    ############################################################################
    # CONSTRUCTORS / DESTRUCTOR
    ############################################################################

    def __init__(self, _oDaemon: "Daemon", _sName: str, _bVerbose: bool, _bRespawn: bool):
        """Constructor.

        Args:
            _oDameon: Parent daemon
            _sName: Watcher name
            _bVerbose: Log output data
            _bRespawn: Respawn watcher in case of error
        """
        # Fields
        self.__iPID = os.getpid()
        self.__oDaemon = _oDaemon
        self.__sName = _sName
        self.__bVerbose = _bVerbose
        self.__bRespawn = _bRespawn
        self.__oProducer = None
        self.__bFilter = False
        self.__loFilters = []
        self.__bConditioner = False
        self.__loConditioners = []
        self.__loConsumers = []
        self.__bStop = False
        self.__bDebug = _oDaemon.debug()

    def setProducer(self, _oProducer: "Producer"):
        """Set the data producer.

        Args:
            _oProducer: Log data producer
        """
        if not isinstance(_oProducer, Producer):
            raise RuntimeError("Producer is not a subclass of LogWatcher.Producers.Producer")
        self.__oProducer = _oProducer

    def addFilter(self, _oFilter: "Filter"):
        """Add a data filter.

        Args:
            _oFilter: Log data filter
        """
        if not isinstance(_oFilter, Filter):
            raise RuntimeError("Filter is not a subclass of LogWatcher.Filters.Filter")
        self.__bFilter = True
        self.__loFilters.append(_oFilter)

    def addConditioner(self, _oConditioner: "Conditioner"):
        """Add a data conditioner.

        Args:
            _oConditioner: Log data conditioner
        """
        if not isinstance(_oConditioner, Conditioner):
            raise RuntimeError("Conditioner is not a subclass of LogWatcher.Conditioners.Conditioner")
        self.__bConditioner = True
        self.__loConditioners.append(_oConditioner)

    def addConsumer(self, _oConsumer: "Consumer"):
        """Add a data consumer.

        Args:
            _oConsumer: Log data consumer
        """
        if not isinstance(_oConsumer, Consumer):
            raise RuntimeError("Consumer is not a subclass of LogWatcher.Consumers.Consumer")
        self.__loConsumers.append(_oConsumer)

    ############################################################################
    # METHODS
    ############################################################################

    def pid(self):
        """Return our process ID."""
        return self.__iPID

    def name(self):
        """Returns the watcher name."""
        return self.__sName

    def log(self, sMessage):
        """Log the given message."""
        self.__oDaemon.log(sMessage)

    def feed(self, _sData: str):
        """Feed the producer (raw) data (line) to the watcher.

        This method is to be called by the child producer as log data gets generated.
        The data MUST be fed line-by-line, without trailing newline character.

        Args:
            _sData: Log data (line)
        """
        # Stop ?
        if self.__bStop:
            return
        if self.__bDebug:
            self.__oDaemon.log("DEBUG[Watcher(%s)]: Produced data\n%s\n" % (self.__sName, _sData))

        # Feed the data (string) to the filters (if any)
        oData = None
        if self.__bFilter:
            for oFilter in self.__loFilters:
                try:
                    oData = oFilter.feed(_sData)
                except Exception as e:
                    self.__oDaemon.log("ERROR[Watcher(%s)]: Filter error\n%s\n" % (self.__sName, str(e)))
                    if self.__bDebug:
                        traceback.print_exc()
                    if self.__bRespawn:
                        self.__oDaemon.log("INFO[Watcher(%s)]: Respawning\n" % self.__sName)
                    else:
                        self.__oDaemon.log("ERROR[Watcher(%s)]: Exiting\n" % self.__sName)
                        self.stop()
                    return
                if oData is not None:
                    break
            if oData is None:
                return
        else:
            oData = Data(self.__sName, _sData, _sData)
        if self.__bDebug:
            self.__oDaemon.log("DEBUG[Watcher(%s)]: Filtered data\n%s\n" % (self.__sName, oData.data))

        # Feed the data (object) to the conditioners (if any)
        if self.__bConditioner:
            for oConditioner in self.__loConditioners:
                try:
                    oData = oConditioner.feed(oData)
                except Exception as e:
                    self.__oDaemon.log("ERROR[Watcher(%s)]: Conditioner error\n%s\n" % (self.__sName, str(e)))
                    if self.__bDebug:
                        traceback.print_exc()
                    if self.__bRespawn:
                        self.__oDaemon.log("INFO[Watcher(%s)]: Respawning\n" % self.__sName)
                    else:
                        self.__oDaemon.log("ERROR[Watcher(%s)]: Exiting\n" % self.__sName)
                        self.stop()
                    return
                if oData is None:
                    return
            if self.__bDebug:
                self.__oDaemon.log("DEBUG[Watcher(%s)]: Conditioned data\n%s\n" % (self.__sName, oData.data))

        # Feed the data (object) to the consumers
        if self.__bVerbose:
            self.__oDaemon.log("INFO[Watcher(%s)]: Data: %s\n" % (self.__sName, oData.data))
        for oConsumer in self.__loConsumers:
            try:
                oConsumer.feed(oData)
            except Exception as e:
                self.__oDaemon.log("ERROR[Watcher(%s)]: Consumer error\n%s\n" % (self.__sName, str(e)))
                if self.__bDebug:
                    traceback.print_exc()
                if self.__bRespawn:
                    self.__oDaemon.log("INFO[Watcher(%s)]: Respawning\n" % self.__sName)
                else:
                    self.__oDaemon.log("ERROR[Watcher(%s)]: Exiting\n" % self.__sName)
                    self.stop()
                return

    def run(self):
        """Run the watcher.

        This method will block until the parent daemon is requested to stop and
        the child producer complies.
        """
        # Checks
        if self.__oProducer is None:
            raise RuntimeError("Watcher has no Producer")
        if not len(self.__loConsumers):
            raise RuntimeError("Watcher has no Consumer")

        # Run the producer
        while True:
            if self.__bStop:
                break
            try:
                self.__oProducer.run()
                if not self.__bStop:
                    self.__oDaemon.log("ERROR[Watcher(%s)]: Producer terminated without being stopped\n" % self.__sName)
            except Exception as e:
                self.__oDaemon.log("ERROR[Watcher(%s)]: Producer error\n%s\n" % (self.__sName, str(e)))
                if self.__bDebug:
                    traceback.print_exc()
            if not self.__bStop:
                if self.__bRespawn:
                    self.__oDaemon.log("INFO[Watcher(%s)]: Respawning\n" % self.__sName)
                    continue
                else:
                    self.__oDaemon.log("ERROR[Watcher(%s)]: Exiting\n" % self.__sName)
            self.stop()

    def stop(self):
        """Stop the watcher and exit gracefully."""
        self.__bStop = True
        self.__oProducer.stop()

    def debug(self):
        """Return whether debugging mode is enabled."""
        return self.__bDebug

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
import traceback

# LogWatcher
from .Data import Data
from .Producers import Producer
from .Filters import Filter
from .Consumers import Consumer


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Watcher:
    """
    Log Watcher.

    This class/object correspond to a configured log watcher entity and gathers:
     - one producer
     - zero-to-many filters
     - one-to-many consumers

    Once started, the watcher will in turn start the producer, which will feed its
    output back to it.
    Each output is then fed to the configured filters, each in turn.
    The first matching filter will then return a fully populated data object.
    That data object is then fed to the consumers.
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oDaemon, _sName, _bVerbose):
        """
        Constructor.

        @param  Daemon  _oDameon   Parent daemon
        @param  string  _sName     Watcher name
        @param  bool    _bVerbose  Log filtered (output) data
        """

        # Fields
        self.__iPID = os.getpid()
        self.__oDaemon = _oDaemon
        self.__sName = _sName
        self.__bVerbose = _bVerbose
        self.__oProducer = None
        self.__bFilter = False
        self.__loFilters = []
        self.__loConsumers = []
        self.__bStop = False
        self.__bDebug = _oDaemon.debug()


    def setProducer(self, _oProducer):
        """
        Set the data producer.

        @param  Producer   _oProducer  Log data producer
        """

        if not isinstance(_oProducer, Producer):
            raise RuntimeError('Producer is not a subclass of LogWatcher.Producers.Producer')
        self.__oProducer = _oProducer


    def addFilter(self, _oFilter):
        """
        Add a data filter.

        @param  Filter  _oFilter  Log data filter
        """

        if not isinstance(_oFilter, Filter):
            raise RuntimeError('Filter is not a subclass of LogWatcher.Filters.Filter')
        self.__bFilter = True
        self.__loFilters.append(_oFilter)


    def addConsumer(self, _oConsumer):
        """
        Add a data consumer.

        @param  Consumer  _oConsumer  Log data consumer
        """

        if not isinstance(_oConsumer, Consumer):
            raise RuntimeError('Consumer is not a subclass of LogWatcher.Consumers.Consumer')
        self.__loConsumers.append(_oConsumer)


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def pid(self):
        """
        Return our process ID.
        """

        return self.__iPID


    def name(self):
        """
        Returns the watcher name.
        """

        return self.__sName


    def log(self, sMessage):
        """
        Log the given message.
        """

        self.__oDaemon.log(sMessage)


    def feed(self, _sData):
        """
        Feed the producer (raw) data (line) to the watcher.

        This method is to be called by the child producer as log data gets generated.
        The data MUST be fed line-by-line, without trailing newline character.

        @param  string  _sData  Log data (line)
        """

        # Stop ?
        if self.__bStop: return

        # Feed the data (string) to the filters (if any)
        if self.__bDebug:
            self.__oDaemon.log('DEBUG[Watcher(%s)]: Produced data\n%s\n' % (self.__sName, _sData))
        oData = None
        if self.__bFilter:
            for oFilter in self.__loFilters:
                try:
                    oData = oFilter.feed(_sData)
                except Exception as e:
                    self.__oDaemon.log('ERROR[Watcher(%s)]: Filter error; exiting\n%s\n' % (self.__sName, str(e)))
                    if self.__bDebug:
                        traceback.print_exc()
                    self.stop()
                    return
                if oData is not None:
                    break
            if oData is None:
                return
        else:
            oData = Data(self.__sName, _sData, _sData)
        if self.__bVerbose:
            self.__oDaemon.log('INFO[Watcher(%s)]: Data: %s\n' % (self.__sName, oData.data))
        elif self.__bDebug:
            self.__oDaemon.log('DEBUG[Watcher(%s)]: Filtered data\n%s\n' % (self.__sName, oData.data))

        # Feed the data (object) to the consumers
        for oConsumer in self.__loConsumers:
            try:
                oConsumer.feed(oData)
            except Exception as e:
                self.__oDaemon.log('ERROR[Watcher(%s)]: Consumer error; exiting\n%s\n' % (self.__sName, str(e)))
                if self.__bDebug:
                    traceback.print_exc()
                self.stop()
                return


    def run(self):
        """
        Run the watcher.

        This method will block until the parent daemon is requested to stop and
        the child producer complies.
        """

        # Checks
        if self.__oProducer is None:
            raise RuntimeError('Watcher has no Producer')
        if not len(self.__loConsumers):
            raise RuntimeError('Watcher has no Consumer')

        # Run the producer
        try:
            self.__oProducer.run()
        except Exception as e:
            self.__oDaemon.log('ERROR[Watcher(%s)]: Producer error\n%s\n' % (self.__sName, str(e)))
            if self.__bDebug:
                traceback.print_exc()
        if not self.__bStop:
            self.__oDaemon.log('ERROR[Watcher(%s)]: Producer terminated abnormaly; exiting\n' % self.__sName)
        self.stop()


    def stop(self):
        """
        Stop the watcher and exit gracefully.
        """

        self.__bStop = True
        self.__oProducer.stop()


    def debug(self):
        """
        Return whether debugging mode is enabled.
        """

        return self.__bDebug

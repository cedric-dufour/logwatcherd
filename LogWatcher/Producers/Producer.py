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
from .ProducerQueue import ProducerQueue, Busy
from queue import Empty
from threading import Thread

# LogWatcher
from LogWatcher import Plugin



#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Producer(Plugin):
    """
    Log Data Producer.

    This class is to be inherited by actual producers and described the methods
    expected to be overriden.
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration, _bSynchronous, _bBlocking, _fTimeout):
        """
        Constructor.

        @param  Watcher  _oWatcher        Parent watcher
        @param  string   _sConfiguration  Configuration string (URL query string)
        @param  bool     _bSynchronous    Synchronous flag
        @param  bool     _bBlocking       Blocking flag
        @param  float    _fTimeout        Data feed timeout
        """

        # Parent constructor
        Plugin.__init__(self, _oWatcher, _sConfiguration)

        # Fields
        self.__bSynchronous = _bSynchronous
        self.__bBlocking = _bBlocking
        self.__fTimeout = _fTimeout
        self._bStop = False

        # ... co-worker thread
        if not self.__bSynchronous:
            sThreadName = '%s.Producer' % _oWatcher.name()
            self.__oQueueData = ProducerQueue(1)
            self.__oThreadFeedWatcher = Thread(name=sThreadName, target=self.__feedWatcher)
            self.__oThreadFeedWatcher.start()


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def __feedWatcher(self):
        """
        Error-reporting wrapper around the parent watcher's feed function.

        This wrapper detects when the producer is being stuck by a failing
        filters/consumers chain in its parent watcher.
        """

        while True:
            if self._bStop: break
            try:
                sData = self.__oQueueData.get(timeout=1.0)
                self._oWatcher.feed(sData)
                self.__oQueueData.task_done()
            except Empty:
                pass


    def _feed(self, _sData):
        """
        Feed the data to the parent watcher.

        Unless the producer is configured as synchronous, this method uses a
        co-worker thread to detect whether the parent watcher gets stuck while
        feeding the data to its filters/consumers chain.

        If the producer is set to blocking (the default), this method will block
        until the parent watcher is done feeding the data. If set to non-blocking,
        it will exit immediately and discard (!) the data as long as the parent
        watcher is not done feeding previous data.

        This method SHOULD be called by a producer as part of its run() business
        (rather than feeding the data directly to the parent watcher).
        """

        # Synchronous ?
        if self.__bSynchronous:
            self._oWatcher.feed(_sData)
            return

        # Feed data to the watcher asynchronously (using a the co-worker thread queue)

        # ... check ongoing (non-blocking and timed-out) data feed
        if self.__oQueueData.busy():
            if self.__bBlocking:
                # NB: something is definitely wrong if we get here!...
                raise Exception('Watcher is still feeding previous data')
            else:
                self._oWatcher.log('WARNING[Producer(%s)]: Watcher is still feeding previous data; discarding current data\n' % self._oWatcher.name())
                return

        # ... feed new data
        if self._bDebug:
            self._oWatcher.log('DEBUG[Producer(%s)]: Feeding data asynchronously\n' % self._oWatcher.name())
        self.__oQueueData.put(_sData)

        # ... wait for the watcher to be done with the data
        while True:
            if self._bStop: break
            try:
                self.__oQueueData.join(self.__fTimeout)
            except Busy:
                if self.__bBlocking:
                    self._oWatcher.log('WARNING[Producer(%s)]: Watcher is still feeding previous data; trying again...\n' % self._oWatcher.name())
                    continue
            break


    def stop(self):
        """
        Stop the producer and exit gracefully.
        """

        # Stop
        self._bStop = True


    #------------------------------------------------------------------------------
    # METHODS - TO BE OVERRIDDEN
    #------------------------------------------------------------------------------

    def run(self):
        """
        Run the producer.

        This method must block until the parent watcher is requested to stop and
        it complies gracefully (watching for self._bStop==True).

        The default implementation is to do nothing (exit immediately).
        """

        # Run
        # (this is where your actual producer business ought to be implemented)
        pass

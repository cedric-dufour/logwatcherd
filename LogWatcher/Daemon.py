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
from distutils.util import \
     strtobool
import errno
import signal
import os
import sys
import syslog
import threading
import time
import traceback
import urlparse

# Extra
# ... deb: python-argparse, python-configobj, python-daemon
import argparse
import configobj
from daemon import \
    DaemonContext
from daemon.runner import \
    emit_message, \
    is_pidfile_stale, \
    make_pidlockfile
import validate

# LogWatcher
from LogWatcher import \
     LOGWATCHER_VERSION, \
     LOGWATCHER_CONFIGSPEC, \
    Logger, \
    Watcher


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Daemon:
    """
    Log Watcher Daemon
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self):
        """
        Constructor.
        """

        # Fields
        # ... configuration
        self.__oArgumentParser = None
        self.__oArguments = None
        self.__oConfigObj = None

        # ... runtime
        self.__iPID = os.getpid()
        self.__oLockLog = threading.Lock()
        self.__loWatchers = []
        self.__bStop = False
        self.__bDebug = False

        # Initialization
        self.__initArgumentParser()


    def __initArgumentParser(self):
        """
        Creates the arguments parser (and help generator).
        """

        # Create argument parser
        self.__oArgumentParser = argparse.ArgumentParser(sys.argv[0].split(os.sep)[-1])

        # ... configuration file
        self.__oArgumentParser.add_argument(
            '-c', '--config', type=str,
            metavar='<conf-file>',
            default='/etc/logwatcherd.conf',
            help='Path to configuration file (default:/etc/logwatcherd.conf)')

        # ... PID file
        self.__oArgumentParser.add_argument(
            '-p', '--pid', type=str,
            metavar='<pid-file>',
            default='/var/run/logwatcherd.pid',
            help='Path to daemon PID file (default:/var/run/logwatcherd.pid)')

        # ... remain in foreground
        self.__oArgumentParser.add_argument(
            '-f', '--foreground', action='store_true',
            default=False,
            help='Do not fork to background / Remain on foreground')

        # ... debug
        self.__oArgumentParser.add_argument(
            '-d', '--debug', action='store_true',
            default=False,
            help='Enable debugging messages')

        # ... version
        self.__oArgumentParser.add_argument(
            '-v', '--version', action='version',
            version=('logwatcherd - %s - Cedric Dufour <http://cedric.dufour.name>\n' % LOGWATCHER_VERSION))


    def __initArguments(self, _aArguments=None):
        """
        Parses the command-line arguments; returns a non-zero exit code in case of failure.
        """

        # Parse arguments
        if _aArguments is None:
             _aArguments = sys.argv
        try:
            self.__oArguments = self.__oArgumentParser.parse_args()
        except Exception as e:
            self.__oArguments = None
            sys.stderr.write('ERROR[Daemon]: Failed to parse arguments; %s\n' % str(e))
            return errno.EINVAL

        return 0


    def __initConfigObj(self):
        """
        Loads configuration settings; returns a non-zero exit code in case of failure.
        """

        # Load configuration settings
        try:
            self.__oConfigObj = configobj.ConfigObj(
                self.__oArguments.config,
                configspec=LOGWATCHER_CONFIGSPEC,
                file_error=True)
        except Exception as e:
            self.__oConfigObj = None
            sys.stderr.write('ERROR[Daemon]: Failed to load configuration from file; %s\n' % str(e))
            return errno.ENOENT

        # ... and validate it
        oValidator = validate.Validator()
        oValidatorResult = self.__oConfigObj.validate(oValidator)
        if oValidatorResult != True:
            sys.stderr.write('ERROR[Daemon]: Invalid configuration data\n')
            for(lSectionList, sKey, _) in configobj.flatten_errors(self.__oConfigObj, oValidatorResult):
                if sKey is not None:
                    sys.stderr.write(' > Invalid value/pair (%s:%s)\n' % (', '.join(lSectionList), sKey))
                else:
                    sys.stderr.write(' > Missing/incomplete section (%s)\n' % ', '.join(lSectionList))
            return errno.EINVAL

        return 0


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def pid(self):
        """
        Return our process ID.
        """

        return self.__iPID


    def __startWatcher(self, _oWatcher):
        _oWatcher.run()


    def __spawnWatchers(self, _oConfigObj):
        """
        Create threads corresponding to each configured watcher; returns a non-zero exit code in case of failure.
        """

        # Loop through configured watchers (<=> sections)
        for sWatcherName in list(_oConfigObj.keys()):
            if sWatcherName=='LogWatcher':
                continue  # global configuration

            dWatcherConfig = _oConfigObj[sWatcherName]
            dWatcherConfig_keys = list(dWatcherConfig.keys())

            # Enable ?
            if 'enable' in dWatcherConfig_keys and not strtobool(dWatcherConfig['enable']):
                if self.__bDebug:
                    sys.stderr.write('DEBUG[Daemon(%s)]: Watcher is disabled; skipping\n' % sWatcherName)
                continue

            # Verbose ?
            bVerbose = False
            if 'verbose' in dWatcherConfig_keys:
                bVerbose = strtobool(dWatcherConfig['verbose'])

            # Watcher
            oWatcher = Watcher(self, sWatcherName, bVerbose)

            # Synchronous
            bSynchronous = True
            if 'synchronous' in dWatcherConfig_keys:
                 bSynchronous = strtobool(dWatcherConfig['synchronous'])

            # Blocking
            bBlocking = True
            if 'blocking' in dWatcherConfig_keys:
                 bBlocking = strtobool(dWatcherConfig['blocking'])

            # Timeout
            fTimeout = 5.0
            if 'timeout' in dWatcherConfig_keys:
                try:
                    fTimeout = float(dWatcherConfig['timeout'])
                    if fTimeout<0.0:
                        raise ValueError('Value must me greater or equal to zero')
                except ValueError:
                    sys.stderr.write('ERROR[Daemon(%s)]: Invalid timeout value; using default\n' % sWatcherName)

            # Producer
            if not 'producer' in dWatcherConfig_keys:
                sys.stderr.write('ERROR[Daemon(%s)]: Watcher must define a producer\n' % sWatcherName)
                continue
            if not isinstance(dWatcherConfig['producer'], str):
                sys.stderr.write('ERROR[Daemon(%s)]: Invalid producer definition\n' % sWatcherName)
                continue
            dPluginConfig = urlparse.urlparse(dWatcherConfig['producer'])
            sPluginName = dPluginConfig.path
            try:
                oPluginClass = getattr(__import__('LogWatcher.Producers.%s' % sPluginName, fromlist=['LogWatcher.Producers']), sPluginName)
                oProducer = oPluginClass(oWatcher, dPluginConfig.query, bSynchronous, bBlocking, fTimeout)
                oWatcher.setProducer(oProducer)
                if self.__bDebug:
                    sys.stderr.write('DEBUG[Daemon(%s)]: Producer instantiated (%s)\n' % (sWatcherName, sPluginName))
            except Exception as e:
                sys.stderr.write('ERROR[Daemon(%s)]: Invalid producer (%s)\n%s\n' % (sWatcherName, sPluginName, str(e)))
                if self.__bDebug:
                    traceback.print_exc()
                continue

            # Filters
            if 'filters' in dWatcherConfig_keys:
                lPlugins = dWatcherConfig['filters']
                if isinstance(lPlugins, str):
                    lPlugins = [lPlugins]
                try:
                    for sPluginConfig in lPlugins:
                        dPluginConfig = urlparse.urlparse(sPluginConfig)
                        sPluginName = dPluginConfig.path
                        try:
                            oPluginClass = getattr(__import__('LogWatcher.Filters.%s' % sPluginName, fromlist=['LogWatcher.Filters']), sPluginName)
                            oFilter = oPluginClass(oWatcher, dPluginConfig.query)
                            oWatcher.addFilter(oFilter)
                            if self.__bDebug:
                                sys.stderr.write('DEBUG[Daemon(%s)]: Filter instantiated (%s)\n' % (sWatcherName, sPluginName))
                        except Exception as e:
                            sys.stderr.write('ERROR[Daemon(%s)]: Invalid filter (%s)\n%s\n' % (sWatcherName, sPluginName, str(e)))
                            if self.__bDebug:
                                traceback.print_exc()
                            raise
                except Exception:
                    continue

            # Consumers
            if not 'consumers' in dWatcherConfig_keys:
                sys.stderr.write('ERROR[Daemon(%s)]: Watcher must define at least one consumer\n' % sWatcherName)
                continue
            lPlugins = dWatcherConfig['consumers']
            if isinstance(lPlugins, str):
                lPlugins = [lPlugins]
            try:
                for sPluginConfig in lPlugins:
                    dPluginConfig = urlparse.urlparse(sPluginConfig)
                    sPluginName = dPluginConfig.path
                    try:
                        oPluginClass = getattr(__import__('LogWatcher.Consumers.%s' % sPluginName, fromlist=['LogWatcher.Consumers']), sPluginName)
                        oConsumer = oPluginClass(oWatcher, dPluginConfig.query)
                        oWatcher.addConsumer(oConsumer)
                        if self.__bDebug:
                            sys.stderr.write('DEBUG[Daemon(%s)]: Consumer instantiated (%s)\n' % (sWatcherName, sPluginName))
                    except Exception as e:
                        sys.stderr.write('ERROR[Daemon(%s)]: Invalid consumer (%s)\n%s\n' % (sWatcherName, sPluginName, str(e)))
                        if self.__bDebug:
                            traceback.print_exc()
                        raise
            except Exception:
                continue

            # Add watcher
            self.__loWatchers.append(oWatcher)
            # ... thread
            sThreadName = '%s.Watcher' % sWatcherName
            oThread = threading.Thread(name=sThreadName, target=self.__startWatcher, args=[oWatcher])
            oThread.start()
            if self.__bDebug:
                sys.stderr.write('DEBUG[Daemon(%s)]: Watcher thread started\n' % sWatcherName)

        # Watchers
        iWatchers = len(self.__loWatchers)
        sys.stderr.write('INFO[Daemon]: %d watchers activated\n' % iWatchers)

        # Wait until all watchers exit
        while True:

            # Stop ?
            if self.__bStop:
                iStopAttempts = 12
                while True:
                    iStopAttempts -= 1
                    loThreadsActive =  threading.enumerate()
                    iThreadsActive = len(loThreadsActive)
                    if iStopAttempts<0:
                        for oThread in loThreadsActive:
                            sys.stderr.write('ERROR[Daemon(%s)]: Watcher failed to terminate in time\n' % oThread.name)
                        sys.stderr.write('ERROR[Daemon]: Watchers failed to terminate in time; exiting ungracefully\n')
                        break
                    if iThreadsActive>1:
                        if self.__bDebug:
                            sys.stderr.write('DEBUG[Daemon]: Stopping / Waiting for %d threads to terminate\n' % (iThreadsActive-1))
                        time.sleep(5)
                    else:
                        break
                break

            # Check watchers threads
            loThreadsActive =  threading.enumerate()
            iThreadsActive = len(loThreadsActive)
            if iThreadsActive>1:
                iThreadsWatchers = 0
                for oThread in loThreadsActive:
                    if oThread.name[-7:]=='Watcher':
                        iThreadsWatchers += 1
                if iThreadsWatchers!=iWatchers:
                    sys.stderr.write('WARNING[Daemon]: Only %d/%d watchers are running\n' % (iThreadsWatchers, iWatchers))
                if self.__bDebug:
                    sys.stderr.write('DEBUG[Daemon]: All %d watchers are running\n' % iThreadsWatchers)
            else:
                sys.stderr.write('ERROR[Daemon]: No more threads are running; exiting\n')
                break

            # Sleep
            time.sleep(5)

        # Done
        sys.stderr.write('INFO[Daemon]: Done\n')


    def __syslog(self, _sMessage):
        iLevel = syslog.LOG_INFO
        if _sMessage.find('ERROR') >= 0:
            iLevel = syslog.LOG_ERR
        elif _sMessage.find('WARNING') >= 0:
            iLevel = syslog.LOG_WARNING
        elif _sMessage.find('DEBUG') >= 0:
            iLevel = syslog.LOG_DEBUG
        syslog.syslog(iLevel, _sMessage)


    def __signal(self, signal, frame):
        self.stop()


    def __daemon(self):
        """
        Daemonizes the process; returns a non-zero exit code in case of failure.
        """

        # Daemonize
        try:
            # Create and check PID file
            oPidLockFile = make_pidlockfile(self.__oArguments.pid, 0)
            if is_pidfile_stale(oPidLockFile):
                oPidLockFile.break_lock()
            if oPidLockFile.is_locked():
                sys.stderr.write('ERROR[Daemon]: Daemon process already running; PID=%s\n' % oPidLockFile.read_pid())
                return errno.EEXIST

            # Create daemon context
            oDaemonContext = DaemonContext(pidfile=oPidLockFile)
            oDaemonContext.signal_map = { signal.SIGTERM: self.__signal }
            oDaemonContext.open()
            emit_message('[%s]' % os.getpid())

            # Redirect standard error to syslog
            syslog.openlog('LogWatcher', syslog.LOG_PID, syslog.LOG_DAEMON)
            sys.stderr = Logger(self.__syslog)

            # Execute
            return self.__spawnWatchers(self.__oConfigObj)
        except Exception as e:
            sys.stderr.write('ERROR[Daemon]: Failed to fork to background; %s\n' % str(e))
            return errno.ESRCH


    def log(self, sMessage):
        """
        [thread-safe] Log the given message.
        """

        self.__oLockLog.acquire()
        sys.stderr.write(sMessage)
        self.__oLockLog.release()


    def run(self):
        """
        Run the daemon; returns a non-zero exit code in case of failure.
        """

        # Initialize

        # ... arguments
        iReturn = self.__initArguments()
        if iReturn:
            return iReturn

        # ... configuration
        iReturn = self.__initConfigObj()
        if iReturn:
            return iReturn

        # Configure daemon
        self.__bDebug = self.__oArguments.debug or self.__oConfigObj['LogWatcher']['debug']

        # Fork to background (?)
        if not self.__oArguments.foreground:
            if self.__bDebug:
                sys.stderr.write('DEBUG[Daemon]: Starting background daemon\n')
            return self.__daemon()

        # Foreground processing
        if self.__bDebug:
            sys.stderr.write('DEBUG[Daemon]: Starting foreground processing\n')
        signal.signal(signal.SIGINT, self.__signal)
        signal.signal(signal.SIGTERM, self.__signal)
        return self.__spawnWatchers(self.__oConfigObj)


    def stop(self):
        """
        Stop the daemon and exit gracefully.
        """

        sys.stderr.write('INFO[Daemon]: Stop request received; stopping...\n')
        self.__bStop = True
        for oWatcher in self.__loWatchers:
            oWatcher.stop()


    def debug(self):
        """
        Return whether debugging mode is enabled.
        """

        return self.__bDebug
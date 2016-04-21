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
import socket
import syslog
import time
import urlparse

# LogWatcher
from LogWatcher.Consumers import Consumer


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Syslog(Consumer):
    """
    Syslog Consumer.

    This consumer writes the provided data to the configured syslog facility.

    Configuration parameters are:
     - [opt] host=<string> (default: 'localhost')
             Server host name
     - [opt] port=<int> (default: 514)
             Server port
     - [opt] tcp (flag)
             Connect via TCP (instead of UDP)
     - [opt] socket=<string>
             Local UNIX socket (overrides host/port above)
     - [opt] facility=<string> (default: 'USER')
             Syslog facility
     - [opt] level=<string> (default: 'INFO')
             Syslog level
     - [opt] prefix=<string>
             Prefix data written to syslog
     - [opt] suffix=<string>
             Suffix data written to syslog

    Please refer to 'man 3 syslog' for the list of supported syslog facilities
    and levels.

    Example (watcher configuration):
     - consumers = Syslog?socket=/dev/log&facility=AUTH&level=CRIT,
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration):
        # Parent constructor
        Consumer.__init__(self, _oWatcher, _sConfiguration)

        # Configuration
        dConfiguration = urlparse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... host
        self.__sHost = 'localhost'
        if 'host' in dConfiguration_keys:
            self.__sHost = dConfiguration['host'][0]

        # ... port
        self.__iPort = 514
        if 'port' in dConfiguration_keys:
            try:
                self.__iPort = int(dConfiguration['port'][0])
                if self.__iPort<0:
                    raise ValueError('Value must me greater than zero')
            except Exception:
                _oWatcher.log('ERROR[Producer:Syslog(%s)]: Invalid \'port\' configuration parameter\n' % _oWatcher.name())
                raise

        # ... protocol
        self.__iProtocol = socket.SOCK_DGRAM
        if 'tcp' in dConfiguration_keys:
            self.__iProtocol = socket.SOCK_STREAM

        # ... UNIX socket
        self.__sSocket = None
        if 'socket' in dConfiguration_keys:
            self.__sSocket = dConfiguration['socket'][0]

        # ... facility
        self.__iFacility = syslog.LOG_USER
        if 'facility' in dConfiguration_keys:
            dFacilities = {
                'AUTH': syslog.LOG_AUTH,
                'CRON': syslog.LOG_CRON,
                'DAEMON': syslog.LOG_DAEMON,
                'KERN': syslog.LOG_KERN,
                'LOCAL0': syslog.LOG_LOCAL0,
                'LOCAL1': syslog.LOG_LOCAL1,
                'LOCAL2': syslog.LOG_LOCAL2,
                'LOCAL3': syslog.LOG_LOCAL3,
                'LOCAL4': syslog.LOG_LOCAL4,
                'LOCAL5': syslog.LOG_LOCAL5,
                'LOCAL6': syslog.LOG_LOCAL6,
                'LOCAL7': syslog.LOG_LOCAL7,
                'LPR': syslog.LOG_LPR,
                'MAIL': syslog.LOG_MAIL,
                'NEWS': syslog.LOG_NEWS,
                'SYSLOG': syslog.LOG_SYSLOG,
                'USER': syslog.LOG_USER,
                'UUCP': syslog.LOG_UUCP,
            }
            sFacility = dConfiguration['facility'][0].upper()
            if sFacility in dFacilities.keys():
                self.__iFacility = dFacilities[sFacility]
            else:
                _oWatcher.log('ERROR[Consumer:Syslog(%s)]: Invalid \'facility\' configuration parameter\n' % _oWatcher.name())
                raise ValueError('Syslog facility must be among AUTH, CRON, DAEMON, KERN, LOCAL{0..7}, LPR, MAIL, NEWS, SYSLOG, USER or UUCP')

        # ... level
        self.__iLevel = syslog.LOG_INFO
        if 'level' in dConfiguration_keys:
            dLevels = {
            'EMERG': syslog.LOG_EMERG,
            'ALERT': syslog.LOG_ALERT,
            'CRIT': syslog.LOG_CRIT,
            'ERR': syslog.LOG_ERR,
            'WARNING': syslog.LOG_WARNING,
            'NOTICE': syslog.LOG_NOTICE,
            'INFO': syslog.LOG_INFO,
            'DEBUG': syslog.LOG_DEBUG,
            }
            sLevel = dConfiguration['level'][0].upper()
            if sLevel in dLevels.keys():
                self.__iLevel = dLevels[sLevel]
            else:
                _oWatcher.log('ERROR[Consumer:Syslog(%s)]: Invalid \'level\' configuration parameter\n' % _oWatcher.name())
                raise ValueError('Syslog level must be among EMERG, ALERT, CRIT, ERR, WARNING, NOTICE, INFO or DEBUG')

        # ... prefix
        self.__sPrefix = ''
        if 'prefix' in dConfiguration_keys:
            self.__sPrefix = dConfiguration['prefix'][0]

        # ... suffix
        self.__sSuffix = ''
        if 'suffix' in dConfiguration_keys:
            self.__sSuffix = dConfiguration['suffix'][0]

        # Socket
        # NOTE: we must implement our own socket-level client since Python standard syslog
        #       libraries are too closely tied to Python logging API
        self.__oSocket = None
        self.__setHostPort = (self.__sHost, self.__iPort)
        if self.__sSocket is None:
            # Network
            try:
                self.__initSocketNetwork()
            except socket.error:
                _oWatcher.log('ERROR[Consumer:Syslog(%s)]: Failed to open network connection\n' % _oWatcher.name())
                raise
        else:
            # UNIX
            try:
                self.__initSocketUNIX()
            except socket.error:
                _oWatcher.log('ERROR[Consumer:Syslog(%s)]: Failed to open UNIX socket\n' % _oWatcher.name())
                raise

        # Syslog MSG formatter
        # REF: https://tools.ietf.org/html/rfc5424
        #self.__sFormatter = '<PRIORITY>VERSION TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG'
        # self.__sFormatter = '<%d>1 %%s %s LogWatcher/%s %d - - %%s' % (
        #     (self.__iFacility<<3)|self.__iLevel,
        #     socket.getfqdn(),
        #     _oWatcher.name(),
        #     _oWatcher.pid()
        # )
        # ... well, actually, it seems all this sophistication is not needed...
        self.__sFormatter = '<%d>LogWatcher/%s[%d]: %%s' % (self.__iFacility+self.__iLevel, _oWatcher.name(), _oWatcher.pid())


    def __initSocketNetwork(self):
        self.__oSocket = socket.socket(socket.AF_INET, self.__iProtocol)
        if self.__iProtocol==socket.SOCK_STREAM:
            self.__oSocket.connect(self.__setHostPort)


    def __initSocketUNIX(self):
        self.__oSocket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        try:
            self.__oSocket.connect(self.__sSocket)
        except socket.error:
            self.__oSocket.close()
            self.__oSocket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.__oSocket.connect(self.__sSocket)


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def feed(self, _oData):
        # Write the data to syslog
        sData = '%s%s%s\n' % (self.__sPrefix, _oData.data, self.__sSuffix)
        if self._bDebug:
            self._oWatcher.log('DEBUG[Consumer:Syslog(%s)]: Consumed data\n%s' % (self._oWatcher.name(), sData))
        #sMessage = self.__sFormatter % (time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), sData)
        sMessage = self.__sFormatter % sData
        if self.__sSocket is None:
            # Network
            if self.__iProtocol==socket.SOCK_STREAM:
                self.__oSocket.sendall(sMessage)  # TCP
            else:
                self.__oSocket.sendto(sMessage, self.__setHostPort)  # UDP
        else:
            # UNIX
            try:
                self.__oSocket.send(sMessage)
            except socket.error:
                self.__initSocketUNIX()
                self.__oSocket.send(sMessage)

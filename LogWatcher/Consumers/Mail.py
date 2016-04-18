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
from email.mime.text import \
    MIMEText
import smtplib
import socket
from subprocess import \
    Popen, \
    PIPE
import urlparse

# LogWatcher
from LogWatcher.Consumers import Consumer


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Mail(Consumer):
    """
    E-Mail Sender Consumer.

    This consumer sends the provided data to the given mail recipient.

    Configuration parameters are:
     - [OPTIONAL]  host=<string>:     server host name (default: localhost)
     - [OPTIONAL]  port=<int>:        server port (default: 25)
     - [OPTIONAL]  sendmail=<string>: path to local sendmail binary (overrides host/port above)
     - [OPTIONAL]  from=<email>:      sender address (default: "logwatcherd@%{hostname}")
     - [MANDATORY] to=<email>:        recipient address
     - [OPTIONAL]  subject=<string>:  e-mail subject (default: "LogWatcher/%{watcher}: %{data}")
     - [OPTIONAL]  template=<file>:   e-mail body template file

    In addition, the following "magic snippets" can be used to insert specific data in the
    e-mail subject or body template:
     - '%{hostname}': the local host name
     - '%{watcher}':  the watcher name
     - '%{data}':     the filter (output) data
     - '%{data_raw}': the producer (raw) data
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _oWatcher, _sConfiguration):
        # Parent constructor
        Consumer.__init__(self, _oWatcher, _sConfiguration)

        # Parameters
        self.__sHostname = socket.getfqdn()

        # Configuration
        dConfiguration = urlparse.parse_qs(_sConfiguration, keep_blank_values=True)
        dConfiguration_keys = dConfiguration.keys()

        # ... host
        self.__sHost = 'localhost'
        if 'host' in dConfiguration_keys:
            self.__sHost = dConfiguration['host'][0]

        # ... port
        self.__iPort = 25
        if 'port' in dConfiguration_keys:
            try:
                self.__iPort = int(dConfiguration['port'][0])
                if self.__iPort<0:
                    raise ValueError('Value must me greater than zero')
            except Exception:
                _oWatcher.log('ERROR[Consumer:Mail(%s)]: Invalid \'port\' configuration parameter\n' % _oWatcher.name())
                raise

        # ... sendmail path
        self.__sSendmail = None
        if 'sendmail' in dConfiguration_keys:
            self.__sSendmail = dConfiguration['sendmail'][0]

        # ... from
        self.__sFrom = 'logwatcherd@%s' % self.__sHostname
        if 'from' in dConfiguration_keys:
            self.__sFrom = dConfiguration['from'][0]

        # ... to
        if 'to' not in dConfiguration_keys:
            _oWatcher.log('ERROR[Consumer:Mail(%s)]: Missing \'to\' configuration parameter\n' % _oWatcher.name())
            raise RuntimeError('Missing \'to\' configuration parameter')
        self.__sTo = dConfiguration['to'][0]

        # ... subject
        self.__sSubject = 'LogWatcher/%{watcher}: %{data}'
        if 'subject' in dConfiguration_keys:
            self.__sSubject = dConfiguration['subject'][0]

        # ... template
        self.__sTemplate = '''
This is the Log Watcher Daemon (logwatcherd) running on %{hostname}.

I just got the following data for your attention:

  Watcher: %{watcher}
  Data:    %{data}
  Raw:     %{data_raw}
'''
        if 'template' in dConfiguration_keys:
            try:
                with open(dConfiguration['template'][0], 'r') as oFile:
                    self.__sTemplate = oFile.read()
            except Exception:
                _oWatcher.log('ERROR[Consumer:Mail(%s)]: Invalid \'template\' configuration parameter\n' % _oWatcher.name())
                raise


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def feed(self, _oData):
        # Build the mail message
        # ... body
        sBody = self.__sTemplate
        sBody = sBody.replace('%{hostname}', self.__sHostname) \
            .replace('%{watcher}', _oData.watcher) \
            .replace('%{data}', _oData.data) \
            .replace('%{data_raw}', _oData.data_raw)
        # ... subject
        sSubject = self.__sSubject
        sSubject = sSubject.replace('%{hostname}', self.__sHostname) \
            .replace('%{watcher}', _oData.watcher) \
            .replace('%{data}', _oData.data) \
            .replace('%{data_raw}', _oData.data_raw)
        # ... headers
        oMIMEText = MIMEText( sBody, 'plain', 'utf-8' )
        oMIMEText['From'] = self.__sFrom
        oMIMEText['To'] = self.__sTo
        oMIMEText['Subject'] = sSubject

        # Send the mail message
        if self._bDebug:
            self._oWatcher.log('DEBUG[Consumer:Mail(%s)]: Consumed data\n%s\n' % (self._oWatcher.name(), oMIMEText.as_string()))
        if self.__sSendmail is None:
            # SMTP
            oSTMP = smtplib.SMTP(self.__sHost, self.__iPort)
            oSTMP.sendmail(self.__sFrom, self.__sTo, oMIMEText.as_string())
            oSTMP.quit()
        else:
            # Sendmail
            oPopen = Popen([self.__sSendmail, '-t'], stdin=PIPE)
            oPopen.communicate(oMIMEText.as_string())

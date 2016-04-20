#!/usr/bin/env python2
# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent

# Modules
from distutils.core import setup
import os

# Setup
setup(
    name = 'logwatcherd',
    description = 'Log Watcher Daemon',
    long_description = \
"""
The objective of the Log Watcher Daemon (logwatcherd) is to provide a simple and
modular way to watch logs for specific events and take appropriate corresponding
actions.

It consists of a Python daemon that spawns multiple "watcher" threads, defined
in a single configuration file.

Each watcher consists of:
 - one "Producer", which generates data that may be of interest;
   e.g. watching the content of a log file
 - zero-to-many "Filter(s)", which extract meaningful data from the producer;
   e.g. looking for failed login attempts
 - zero-to-many "Conditioner(s)", which further filter or modify the data;
   e.g. excluding IP addresses from the LAN
 - one-to-many "Consumer(s)", which take actions based on that data
   e.g. add an IP address to an iptables blacklist

Producers, filters, conditioners and consumers are all plugins. A set of basic
plugins are provided as part of the Log Watcher Daemon codebase:

Producer plugins:
 - "Read": dump the content of a given file (cat ...)
 - "Tail": watch content being added to a given file (tail -F ...)

Filter plugins:
 - "Grep": match data based on a given regular expression
 - "Awk": match data field based on a given regular expression

Conditioner plugins:
 - "Sed": match (and replace) data based on a given regular expression

Consumer plugins:
 - "Write": write or append data to a given file
 - "Mail": send data to a given e-mail recipient
 - "Syslog": log data to a given syslog facility

Plugins are very easy and straight-forward to write and integrate with the Log
Watcher Daemon, thus allowing users to address even the most exotic use cases.

With ad-hoc watchers, the Log Watcher Dameon can be made a simple Intrusion
Detection System. Coupled with dynamic firewall configuration (e.g. along
iptables 'recent' module), it can become a simple Intrusion Prevention System.

On the other hand, the Log Watcher Daemon is not about performances and allowing
to monitor a 10gb/s network link on a core routing host. Its goal is being
lightweight and simple, and its purpose is being distributed on each host that
provides some service (e.g. a virtual machine providing SSH remote access).

""",
    version = os.getenv('VERSION'),
    author = 'Cedric Dufour',
    author_email = 'http://cedric.dufour.name',
    license = 'GPL-3',
    url = 'https://github.com/cedric-dufour/logwatcherd',
    download_url = 'https://github.com/cedric-dufour/logwatcherd',
    packages = [ 'LogWatcher', 'LogWatcher.Producers', 'LogWatcher.Filters', 'LogWatcher.Conditioners', 'LogWatcher.Consumers' ],
    requires = [ 'argparse', 'configobj', 'daemon' ],
    scripts = [ 'logwatcherd' ],
    )

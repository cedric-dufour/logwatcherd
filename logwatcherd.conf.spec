[LogWatcher]
debug = boolean(default=False)
delay = integer(min=0, max=300, default=0)
includes = string_list(min=0, default=list())

[__many__]
enable = boolean(default=True)
verbose = boolean(default=False)
respawn = boolean(default=False)
synchronous = boolean(default=True)
blocking = boolean(default=True)
timeout = float(min=0.001, max=60.0, default=5.0)
producer = string(min=1)
filters = string_list(min=0, default=list())
conditioners = string_list(min=0, default=list())
consumers = string_list(min=1)

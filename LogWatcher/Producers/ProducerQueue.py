# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent

#------------------------------------------------------------------------------
# DEPENDENCIES
#------------------------------------------------------------------------------

# Standard
from Queue import Queue
from time import time


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class Busy(Exception):
    """
    Exception raised by ProducerQueue.join() timeout.
    """

    pass


class ProducerQueue(Queue):
    """
    A extended version of Python Queue class which adds a timeout to its join()
    method.
    """

    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def busy(self):
        """
        Returns whether the queue has unfinished tasks.
        """

        self.all_tasks_done.acquire()
        b = self.unfinished_tasks>0
        self.all_tasks_done.release()
        return b


    def join(self, timeout=None):
        if timeout is None:
            return Queue.join()

        # REF: http://stackoverflow.com/questions/1564501/add-timeout-argument-to-pythons-queue-join
        self.all_tasks_done.acquire()
        try:
            endtime = time() + timeout
            while self.unfinished_tasks:
                remaining = endtime - time()
                if remaining <= 0.0:
                    raise Busy
                self.all_tasks_done.wait(remaining)
        finally:
            self.all_tasks_done.release()

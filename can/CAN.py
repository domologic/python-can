"""
The core of python-can - contains implementations of all
the major classes in the library, which form abstractions of the
functionality provided by each CAN interface.

Copyright (C) 2010 Dynamic Controls
"""

import logging
try:
    import queue
except ImportError:
    import Queue as queue


logging.basicConfig(level=logging.WARNING)
log = logging.getLogger('CAN')

log.debug("Loading python-can")


def set_logging_level(level_name=None):
    """Set the logging level for python-can.
    Expects one of: 'critical', 'error', 'warning', 'info', 'debug', 'subdebug'
    """
    try:
        log.setLevel(getattr(logging, level_name.upper()))
    except:
        log.setLevel(logging.DEBUG)


def use(backend=None):
    """
    
    """
    pass


class Listener(object):
    def on_message_received(self, msg):
        raise NotImplementedError(
            "{} has not implemented on_message_received".format(
                self.__class__.__name__)
            )
    
    def __call__(self, msg):
        return self.on_message_received(msg)


class BufferedReader(Listener):

    def __init__(self):
        self.buffer = queue.Queue(0)

    def on_message_received(self, msg):
        self.buffer.put(msg)

    def get_message(self):
        try:
            return self.buffer.get(timeout=0.5)
        except queue.Empty:
            return None


class Printer(Listener):
    def on_message_received(self, msg):
        print(msg)


class CSVWriter(Listener):
    def __init__(self, filename):
        self.csv_file = open(filename, 'wt')
        
        # Write a header row
        self.csv_file.write("timestamp, arbitrationid, flags, dlc, data")

    def on_message_received(self, msg):
        row = ','.join([msg.timestamp, 
                        msg.arbitration_id, 
                        msg.flags, 
                        msg.dlc, 
                        msg.data])
        self.csv_file.write(row + '\n')

    def __del__(self):
        self.csv_file.close()
        super(CSVWriter, self).__del__()


class SqliteWriter(Listener):
    def __init__(self, filename):
        self.db_file = open(filename, 'wt')

        # create table structure
        raise NotImplementedError("TODO")
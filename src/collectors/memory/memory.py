# coding=utf-8

"""
This class collects data on memory utilization

Note that MemFree may report no memory free. This may not actually be the case,
as memory is allocated to Buffers and Cache as well. See
[this link](http://www.linuxatemyram.com/) for more details.

#### Dependencies

* /proc/meminfo or psutil

"""

import diamond.collector
import diamond.convertor
import os
from diamond.collector import str_to_bool

try:
    import psutil
    psutil  # workaround for pyflakes issue #13
except ImportError:
    psutil = None

_KEY_MAPPING = [
    'MemTotal',
    'MemFree',
    'Buffers',
    'Cached',
    'Active',
    'Dirty',
    'Inactive',
    'Shmem',
    'SwapTotal',
    'SwapFree',
    'SwapCached',
    'VmallocTotal',
    'VmallocUsed',
    'VmallocChunk'
]


class MemoryCollector(diamond.collector.Collector):

    PROC = '/proc/meminfo'

    def get_default_config_help(self):
        config_help = super(MemoryCollector, self).get_default_config_help()
        config_help.update({
            'detailed':         'Set to True to Collect all the nodes',
            'memory_warn':      'Memory warning threshold',
            'memory_crit':      'Memory critical threshold',
            'memory_percent':   'Set to True for percent used, or False for bytes available',
            'swap_warn':        'Swap warning threshold',
            'swap_crit':        'Swap critical threshold',
            'swap_percent':      'Set to True for percent used, or False for bytes available',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(MemoryCollector, self).get_default_config()
        config.update({
            'enabled':          'True',
            'path':             'memory',
            'method':           'Threaded',
            # Collect all the nodes or just a few standard ones?
            # Uncomment to enable
            #'detailed': 'True'
            'memory_warn':     '85',
            'memory_crit':     '95',
            'memory_percent':  'True',
            'swap_warn':       '85',
            'swap_crit':       '95',
            'swap_percent':     'True',
        })
        return config

    def collect(self):
        """
        Collect memory stats
        """
        if os.access(self.PROC, os.R_OK):
            file = open(self.PROC)
            data = file.read()
            file.close()

            for line in data.splitlines():
                try:
                    name, value, units = line.split()
                    name = name.rstrip(':')
                    value = int(value)

                    if (name not in _KEY_MAPPING
                            and 'detailed' not in self.config):
                        continue

                    for unit in self.config['byte_unit']:
                        value = diamond.convertor.binary.convert(value=value,
                                                                 oldUnit=units,
                                                                 newUnit=unit)
                        self.publish(name, value, metric_type='GAUGE')

                        # TODO: We only support one unit node here. Fix it!
                        break

                except ValueError:
                    continue
            return True
        else:
            if not psutil:
                self.log.error('Unable to import psutil')
                self.log.error('No memory metrics retrieved')
                return None

            virtual_memory = psutil.virtual_memory()
            swap_memory = psutil.swap_memory()
            units = 'B'

            # Determine if load exceeds warning/critical status
            if str_to_bool(self.config['memory_percent']):
                if (virtual_memory.percent > self.config['memory_crit']):
                    virtual_memory_state = 'critical'
                elif (virtual_memory.percent > self.config['memory_warn']):
                    virtual_memory_state = 'warning'
                else:
                    virtual_memory_state = 'ok'
            else:
                if (virtual_memory.available < self.config['memory_crit']):
                    virtual_memory_state = 'critical'
                elif (virtual_memory.available < self.config['memory_warn']):
                    virtual_memory_state = 'warning'
                else:
                    virtual_memory_state = 'ok'

            if str_to_bool(self.config['swap_percent']):
                if (swap_memory.percent > self.config['swap_crit']):
                    swap_memory_state = 'critical'
                elif (swap_memory.percent > self.config['swap_warn']):
                    swap_memory_state = 'warning'
                else:
                    swap_memory_state = 'ok'
            else:
                if (swap_memory.free < self.config['swap_crit']):
                    swap_memory_state = 'critical'
                elif (swap_memory.free < self.config['swap_warn']):
                    swap_memory_state = 'warning'
                else:
                    swap_memory_state = 'ok'

            for unit in self.config['byte_unit']:
                value = diamond.convertor.binary.convert(
                    value=virtual_memory.total, oldUnit=units, newUnit=unit)
                self.publish('MemTotal', value, metric_type='GAUGE')

                value = diamond.convertor.binary.convert(
                    value=virtual_memory.available, oldUnit=units, newUnit=unit)
                self.publish('MemFree', value, metric_type='GAUGE', state=virtual_memory_state)

                value = diamond.convertor.binary.convert(
                    value=swap_memory.total, oldUnit=units, newUnit=unit)
                self.publish('SwapTotal', value, metric_type='GAUGE')

                value = diamond.convertor.binary.convert(
                    value=swap_memory.free, oldUnit=units, newUnit=unit)
                self.publish('SwapFree', value, metric_type='GAUGE', state=swap_memory_state)

                # TODO: We only support one unit node here. Fix it!
                break

            return True

        return None

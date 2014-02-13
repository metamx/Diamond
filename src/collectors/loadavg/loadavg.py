# coding=utf-8

"""
Uses /proc/loadavg to collect data on load average

#### Dependencies

 * /proc/loadavg

"""

import diamond.collector
import re
import os
import multiprocessing
from diamond.collector import str_to_bool


class LoadAverageCollector(diamond.collector.Collector):

    PROC_LOADAVG = '/proc/loadavg'
    PROC_LOADAVG_RE = re.compile(r'([\d.]+) ([\d.]+) ([\d.]+) (\d+)/(\d+)')

    def get_default_config_help(self):
        config_help = super(LoadAverageCollector,
                            self).get_default_config_help()
        config_help.update({
            'simple':       'Only collect the 1 minute load average',
            'load01_warn':  '1-minute load warning threshold (load average / core)',
            'load01_crit':  '1-minute load critical threshold (load average / core)',
            'load05_warn':  '5-minute load warning threshold (load average / core)',
            'load05_crit':  '5-minute load critical threshold (load average / core)',
            'load15_warn':  '15-minute load warning threshold (load average / core)',
            'load15_crit':  '15-minute load critical threshold (load average / core)',
        })
        return config_help

    def get_default_config(self):
        """
        Returns the default collector settings
        """
        config = super(LoadAverageCollector, self).get_default_config()
        config.update({
            'enabled':      'True',
            'path':         'loadavg',
            'method':       'Threaded',
            'simple':       'False',
            'load01_warn':  '3',
            'load01_crit':  '8',
            'load05_warn':  '3',
            'load05_crit':  '8',
            'load15_warn':  '3',
            'load15_crit':  '8',
        })
        return config

    def collect(self):
        load01, load05, load15 = os.getloadavg()
        cores = multiprocessing.cpu_count()

        # Determine if load exceeds warning/critical status
        if (load01 / cores) > self.config['load01_crit']:
            load01_state = 'critical'
        elif (load01 / cores) > self.config['load01_warn']:
            load01_state = 'warning'
        else:
            load01_state = 'ok'

        if (load05 / cores) > self.config['load05_crit']:
            load05_state = 'critical'
        elif (load05 / cores) > self.config['load05_warn']:
            load05_state = 'warning'
        else:
            load05_state = 'ok'

        if (load15 / cores) > self.config['load15_crit']:
            load015_state = 'critical'
        elif (load15 / cores) > self.config['load15_warn']:
            load15_state = 'warning'
        else:
            load15_state = 'ok'

        if not str_to_bool(self.config['simple']):
            self.publish_gauge('01', load01, 2, state=load01_state)
            self.publish_gauge('05', load05, 2, state=load05_state)
            self.publish_gauge('15', load15, 2, state=load15_state)
        else:
            self.publish_gauge('load', load01, 2, state=load01_state)

        # Legacy: add process/thread counters provided by
        # /proc/loadavg (if available).
        if os.access(self.PROC_LOADAVG, os.R_OK):
            file = open(self.PROC_LOADAVG)
            for line in file:
                match = self.PROC_LOADAVG_RE.match(line)
                if match:
                    self.publish_gauge('processes_running', int(match.group(4)))
                    self.publish_gauge('processes_total', int(match.group(5)))
            file.close()

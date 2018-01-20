from collections import OrderedDict
from datetime import datetime, timezone
import json
import platform
import time

import pytest


class JSONReport:
    """The pytest JSON report plugin."""

    def __init__(self, config):
        self.config = config
        self.start_time = None
        self.report_size = 0
        self.reports = OrderedDict()

    @property
    def report_file(self):
        return self.config.option.json_report_file or \
               self.config.getini('json_report_file') or \
               '.report.json'

    @property
    def show_traceback(self):
        return not self.config.option.json_report_no_traceback

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_runtest_logreport(self, report):
        if report.nodeid in self.reports:
            self.reports[report.nodeid].append(report)
        else:
            self.reports[report.nodeid] = [report]

    def pytest_sessionfinish(self, session):
        duration = time.time() - self.start_time
        json_tests = list(map(self.json_test_result, self.reports.values()))
        json_report = {
            'created': datetime.now(timezone.utc).astimezone().isoformat(),
            'duration': duration,
            'python': platform.python_version(),
            'pytest': pytest.__version__,
            'platform': platform.platform(),
            'tests': json_tests,
        }
        self.save_report(json_report)

    def save_report(self, json_report):
        """Save the test report to JSON file."""
        with open(self.report_file, 'w') as f:
            json.dump(json_report, f)
            self.report_size = f.tell()

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep('-', 'JSON report')
        terminalreporter.write_line('report written to: %s (%d bytes)' %
                                    (self.report_file, self.report_size))

    def total_outcome(self, reports):
        """Return actual test outcome of the group of reports."""
        for report in reports:
            cat = self.config.hook.pytest_report_teststatus(report=report)[0]
            if cat not in ['passed', '']:
                return cat
        return 'passed'

    def json_test_result(self, reports):
        """Return JSON-serializable object for a list of test reports."""
        any_report = reports[0]
        nodeid = any_report.nodeid
        path, line, domain = any_report.location
        keywords = any_report.keywords
        outcome = self.total_outcome(reports)
        stages = {r.when: self.json_stage(r) for r in reports}
        return {
            'nodeid': nodeid,
            'path': path,
            'lineno': line,
            'domain': domain,
            'outcome': outcome,
            'keywords': keywords,
            **stages
        }

    def json_stage(self, report):
        """Return JSON-serializable object for the stage info of a report."""
        duration = report.duration
        outcome = report.outcome
        crash_and_traceback = self.json_crash_and_traceback(report)
        longreprtext = report.longreprtext
        return {
            'duration': duration,
            'outcome': outcome,
            'longrepr': longreprtext,
            **crash_and_traceback
        }

    def json_crash_and_traceback(self, report):
        """Return JSON-serializable object for the crash and traceback."""
        try:
            tb = report.longrepr.reprtraceback
            crash = report.longrepr.reprcrash
        except AttributeError:
            return {}
        traceback = {
            'traceback': [{
                'path': entry.reprfileloc.path,
                'lineno': entry.reprfileloc.lineno,
                'info': entry.reprfileloc.message,
            } for entry in tb.reprentries]
        } if self.show_traceback else {}
        return {
            'crash': {
                # We don't use crash.path because we want the shorthand
                'path': tb.reprentries[-1].reprfileloc.path,
                'lineno': crash.lineno,
                'info': crash.message,
            },
            **traceback
        }


def pytest_addoption(parser):
    file_help_text = 'target path to save JSON report'
    traceback_help_text = 'don\'t include tracebacks in the JSON report'
    group = parser.getgroup('jsonreport', 'reporting test results as JSON')
    group.addoption('--json-report', default=False, action='store_true',
                    help='enable JSON report')
    group.addoption('--json-report-file', help=file_help_text)
    group.addoption('--json-report-no-traceback', default=False,
                    action='store_true', help=traceback_help_text)
    parser.addini('json_report_file', file_help_text)


def pytest_configure(config):
    if not (config.option.json_report or config.getini('json_report_file')):
        return
    plugin = JSONReport(config)
    config._json_report = plugin
    config.pluginmanager.register(plugin)


def pytest_unconfigure(config):
    plugin = getattr(config, '_json_report', None)
    if plugin is not None:
        del config._json_report
        config.pluginmanager.unregister(plugin)

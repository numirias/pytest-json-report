from collections import OrderedDict
from datetime import datetime
import json
import platform
import time

import pytest


class JSONReport:
    """The pytest JSON report plugin."""

    def __init__(self, report_file):
        self.report_file = report_file
        self.reports = OrderedDict()
        self.start_time = None

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_runtest_logreport(self, report):
        if report.nodeid in self.reports:
            self.reports[report.nodeid].append(report)
        else:
            self.reports[report.nodeid] = [report]

    def pytest_sessionfinish(self, session):
        duration = time.time() - self.start_time
        json_tests = [self.json_test_item(r) for r in self.reports.values()]
        json_report = {
            'created': datetime.now().astimezone().isoformat(),
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

    @staticmethod
    def json_test_item(reports):
        """Return JSON-serializable object for a list of test reports."""
        any_report = reports[0]
        nodeid = any_report.nodeid
        path, line, domain = any_report.location
        keywords = any_report.keywords
        outcome = JSONReport.total_outcome(reports)
        stages = {r.when: JSONReport.json_stage(r) for r in reports}
        return {
            'nodeid': nodeid,
            'path': path,
            'line': line,
            'domain': domain,
            'outcome': outcome,
            'keywords': keywords,
            **stages
        }

    @staticmethod
    def total_outcome(reports):
        """Return actual test outcome of the group of report."""
        return next((r.outcome for r in reports if r.outcome != 'passed'),
                    'passed')

    @staticmethod
    def json_stage(report):
        """Return JSON-serializable object for the stage info of a report."""
        duration = report.duration
        outcome = report.outcome
        longrepr = str(report.longrepr) if report.longrepr else None
        return {
            'duration': duration,
            'outcome': outcome,
            'longrepr': longrepr,
        }


def pytest_addoption(parser):
    group = parser.getgroup('jsonreport', 'reporting test results as JSON')
    group.addoption('--json-report', default=False, action='store_true',
                    help='create JSON report')
    group.addoption('--json-report-file', default='.report.json',
                    help='target file to save JSON report')


def pytest_configure(config):
    if not config.option.json_report:
        return
    plugin = JSONReport(config.option.json_report_file)
    config._json_report = plugin
    config.pluginmanager.register(plugin)


def pytest_unconfigure(config):
    plugin = getattr(config, '_json_report', None)
    if plugin is not None:
        del config._json_report
        config.pluginmanager.unregister(plugin)

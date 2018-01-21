from collections import Counter, OrderedDict
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
        self.sections = {}

    @property
    def report_file(self):
        return self.config.option.json_report_file or \
               self.config.getini('json_report_file') or \
               '.report.json'

    @property
    def show_traceback(self):
        return not self.config.option.json_report_no_traceback

    @property
    def show_streams(self):
        return not self.config.option.json_report_no_streams

    @property
    def show_test_details(self):
        return not self.config.option.json_report_summary

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_runtest_logreport(self, report):
        if report.nodeid in self.reports:
            self.reports[report.nodeid].append(report)
        else:
            self.reports[report.nodeid] = [report]

    def pytest_sessionfinish(self, session):
        duration = time.time() - self.start_time
        reports = self.reports.values()
        json_tests = {
            'tests': list(map(self.json_test_result, reports))
        } if self.show_test_details else {}
        json_summary = self.json_summary(reports)
        json_report = {
            'created': datetime.now(timezone.utc).astimezone().isoformat(),
            'duration': duration,
            'python': platform.python_version(),
            'pytest': pytest.__version__,
            'platform': platform.platform(),
            'summary': json_summary,
            **json_tests,
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

    def pytest_runtest_makereport(self, item, call):
        # We need the sections for stdout and stderr
        self.sections[item.nodeid] = item._report_sections[:]

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
        json_longrepr = {
            'longrepr': report.longreprtext,
        } if report.longreprtext else {}
        return {
            'duration': report.duration,
            'outcome': report.outcome,
            **json_longrepr,
            **self.json_streams(report),
            **self.json_crash_and_traceback(report),
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

    def json_streams(self, report):
        """Return JSON-serializable object for the standard stream outputs."""
        if not self.show_streams:
            return {}
        streams = {}
        sections = self.sections[report.nodeid]
        for when, key, content in sections:
            if when != report.when:
                continue
            if key in ['stdout', 'stderr']:
                streams[key] = content
        return streams

    def json_summary(self, reports):
        """Return JSON-serializable object summarizing the test results."""
        summary = Counter([self.total_outcome(r) for r in reports])
        summary['total'] = sum(summary.values())
        return summary


def pytest_addoption(parser):
    file_help_text = 'target path to save JSON report'
    no_traceback_help_text = 'don\'t include tracebacks in JSON report'
    no_stream_help_text = 'don\'t include stdout/stderr output in JSON report'
    summary_help_text = 'just create a summary without per-test details'
    group = parser.getgroup('jsonreport', 'reporting test results as JSON')
    group.addoption('--json-report', default=False, action='store_true',
                    help='create JSON report')
    group.addoption('--json-report-file', help=file_help_text)
    group.addoption('--json-report-no-traceback', default=False,
                    action='store_true', help=no_traceback_help_text)
    group.addoption('--json-report-no-streams', default=False,
                    action='store_true', help=no_stream_help_text)
    group.addoption('--json-report-summary', default=False,
                    action='store_true', help=summary_help_text)
    parser.addini('json_report_file', file_help_text)


def pytest_configure(config):
    if not config.option.json_report:
        return
    plugin = JSONReport(config)
    config._json_report = plugin
    config.pluginmanager.register(plugin)


def pytest_unconfigure(config):
    plugin = getattr(config, '_json_report', None)
    if plugin is not None:
        del config._json_report
        config.pluginmanager.unregister(plugin)

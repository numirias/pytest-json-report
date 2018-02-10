from collections import Counter, OrderedDict
import json
import time

import pytest


class JSONReport:
    """The pytest JSON report plugin."""

    def __init__(self, config):
        self.config = config
        self.start_time = None
        self.report_size = 0
        self.tests = OrderedDict()

    @property
    def report_file(self):
        return self.config.option.json_report_file or \
               self.config.getini('json_report_file') or \
               '.report.json'

    @property
    def show_traceback(self):
        return not self.config.option.json_report_no_traceback and \
               self.config.option.tbstyle != 'no'

    @property
    def show_streams(self):
        return not self.config.option.json_report_no_streams

    @property
    def show_test_details(self):
        return not self.config.option.json_report_summary

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_addhooks(self, pluginmanager):
        pluginmanager.add_hookspecs(Hooks)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        try:
            test = self.tests[item]
        except KeyError:
            test = self.json_test(item)
            self.tests[item] = test
        # Update total test outcome if necessary
        outcome = self.config.hook.pytest_report_teststatus(report=report)[0]
        if outcome not in ['passed', '']:
            test['outcome'] = outcome
        stage = {
            'duration': report.duration,
            'outcome': report.outcome,
            **self.json_crash_and_traceback(report),
        }
        if report.longreprtext:
            stage['longrepr'] = report.longreprtext
        stage.update(self.streams(item, report.when))
        test[call.when] = stage

    def streams(self, item, when):
        if not self.show_streams:
            return {}
        return {key: val for when_, key, val in item._report_sections if
                when_ == when and key in ['stdout', 'stderr']}

    def pytest_sessionfinish(self, session):
        self.add_metadata()
        json_report = {
            'created': time.time(),
            'duration': time.time() - self.start_time,
            'environment': getattr(self.config, '_metadata', {}),
            'summary': self.json_summary(),
        }
        if self.show_test_details:
            json_report['tests'] = list(self.tests.values())
        self.config.hook.pytest_json_modifyreport(json_report=json_report)
        self.save_report(json_report)

    def add_metadata(self):
        for item, test in self.tests.items():
            try:
                metadata = item._json_metadata
            except AttributeError:
                continue
            if metadata == {}:
                continue
            try:
                json.dumps(metadata)
            except TypeError:
                # Metadata isn't JSON-serializable, so make it a str
                metadata = str(metadata)
            test['metadata'] = metadata

    def save_report(self, json_report):
        """Save the test report to JSON file."""
        with open(self.report_file, 'w') as f:
            json.dump(json_report, f)
            self.report_size = f.tell()

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep('-', 'JSON report')
        terminalreporter.write_line('report written to: %s (%d bytes)' %
                                    (self.report_file, self.report_size))

    def total_outcome(self, report_group):
        """Return actual test outcome of the group of reports."""
        for report in report_group.values():
            cat = self.config.hook.pytest_report_teststatus(report=report)[0]
            if cat not in ['passed', '']:
                return cat
        return 'passed'

    def json_test(self, item):
        """Return JSON-serializable object for a list of test reports."""
        path, line, domain = item.location
        return {
            'nodeid': item.nodeid,
            'path': path,
            'lineno': line,
            'domain': domain,
            'keywords': list(item.keywords),
            'outcome': 'passed',  # Will be overridden in case of failure
        }

    def json_crash_and_traceback(self, report):
        """Return JSON-serializable object for the crash and traceback."""
        try:
            tb = report.longrepr.reprtraceback
            crash = report.longrepr.reprcrash
        except AttributeError:
            return {}
        data = {
            'crash': {
                'path': crash.path,
                'lineno': crash.lineno,
                'info': crash.message,
            },
        }
        if self.show_traceback:
            data['traceback'] = [{
                'path': entry.reprfileloc.path,
                'lineno': entry.reprfileloc.lineno,
                'info': entry.reprfileloc.message,
            } for entry in tb.reprentries]
        return data

    def json_summary(self):
        """Return JSON-serializable object summarizing the test results."""
        summary = Counter([t['outcome'] for t in self.tests.values()])
        summary['total'] = sum(summary.values())
        return summary

    @pytest.fixture
    def json_metadata(self, request):
        try:
            metadata = request.node._json_metadata
        except AttributeError:
            metadata = {}
            request.node._json_metadata = metadata
        return metadata


class Hooks:

    def pytest_json_modifyreport(self, json_report):
        """Called after building JSON report and before saving it."""


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

from collections import Counter, OrderedDict
import json
import time

import pytest


class JSONReport:
    """The JSON report pytest plugin."""

    def __init__(self, config):
        self.config = config
        self.start_time = None
        self.tests = OrderedDict()
        self.collectors = []
        self.warnings = []
        self.report = None
        self.report_size = 0

    @property
    def report_file(self):
        return self.config.option.json_report_file or \
               self.config.getini('json_report_file') or \
               '.report.json'

    @property
    def want_traceback(self):
        return not self.config.option.json_report_no_traceback and \
               self.config.option.tbstyle != 'no'

    @property
    def want_streams(self):
        return not self.config.option.json_report_no_streams

    @property
    def want_summary(self):
        return self.config.option.json_report_summary

    def pytest_addhooks(self, pluginmanager):
        pluginmanager.add_hookspecs(Hooks)

    def pytest_sessionstart(self, session):
        self.start_time = time.time()

    def pytest_collectreport(self, report):
        collector = self.json_collector(report)
        if report.longrepr:
            # Unfortunately, the collection report doesn't provide crash
            # details, so we can only add the message, but no traceback etc.
            collector['longrepr'] = str(report.longrepr)
        self.collectors.append(collector)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        try:
            test = self.tests[item]
        except KeyError:
            test = self.json_testitem(item)
            self.tests[item] = test
        # Update total test outcome, if necessary. The total outcome can be
        # different from the outcome of the setup/call/teardown stage.
        outcome = self.config.hook.pytest_report_teststatus(report=report)[0]
        if outcome not in ['passed', '']:
            test['outcome'] = outcome
        test[call.when] = self.json_teststage(item, report)

    def pytest_sessionfinish(self, session):
        self.add_metadata()
        json_report = {
            'created': time.time(),
            'duration': time.time() - self.start_time,
            'exitcode': session.exitstatus,
            'root': str(session.fspath),
            'environment': getattr(self.config, '_metadata', {}),
            'summary': self.json_summary(),
        }
        if not self.want_summary:
            json_report['collectors'] = self.collectors
            json_report['tests'] = list(self.tests.values())
            if self.warnings:
                json_report['warnings'] = self.warnings
        self.config.hook.pytest_json_modifyreport(json_report=json_report)
        self.save_report(json_report)
        # self.report isn't ever used, but it's useful if the report needs to
        # be processed by another script/plugin.
        self.report = json_report

    def pytest_logwarning(self, code, fslocation, message, nodeid):
        self.warnings.append({
            'code': code,
            'path': str(fslocation),
            'nodeid': nodeid,
            'message': message,
        })

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep('-', 'JSON report')
        terminalreporter.write_line('report written to: %s (%d bytes)' %
                                    (self.report_file, self.report_size))

    def add_metadata(self):
        """Add metadata from test items to the report."""
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
        """Save the JSON report to file."""
        with open(self.report_file, 'w') as f:
            json.dump(json_report, f)
            self.report_size = f.tell()

    def json_collector(self, report):
        """Return JSON-serializable collector node."""
        return {
            'nodeid': report.nodeid,
            # This is the outcome of the collection, not the test outcome
            'outcome': report.outcome,
            'children': [{
                'nodeid': node.nodeid,
                'type': node.__class__.__name__,
                **self.json_location(node),
            } for node in report.result],
        }

    def json_location(self, node):
        """Return JSON-serializable node location."""
        try:
            path, line, domain = node.location
        except AttributeError:
            return {}
        return {
            'path': path,
            'lineno': line,
            'domain': domain,
        }

    def json_testitem(self, item):
        """Return JSON-serializable test item."""
        return {
            'nodeid': item.nodeid,
            # Adding the location in the collector dict *and* here appears
            # redundant, but the docs say they may be different
            **self.json_location(item),
            # item.keywords is actually a dict, but we just save the keys
            'keywords': list(item.keywords),
            # The outcome will be overridden in case of failure
            'outcome': 'passed',
        }

    def json_teststage(self, item, report):
        """Return JSON-serializable test stage (setup/call/teardown)."""
        stage = {
            'duration': report.duration,
            'outcome': report.outcome,
            **self.json_crash(report),
            **self.json_traceback(report),
            **self.json_streams(item, report.when),
        }
        if report.longreprtext:
            stage['longrepr'] = report.longreprtext
        return stage

    def json_streams(self, item, when):
        """Return JSON-serializable output of the standard streams."""
        if not self.want_streams:
            return {}
        return {key: val for when_, key, val in item._report_sections if
                when_ == when and key in ['stdout', 'stderr']}

    def json_crash(self, report):
        """Return JSON-serializable crash details."""
        try:
            crash = report.longrepr.reprcrash
        except AttributeError:
            return {}
        return {
            'crash': {
                'path': crash.path,
                'lineno': crash.lineno,
                'message': crash.message,
            },
        }

    def json_traceback(self, report):
        """Return JSON-serializable traceback details."""
        try:
            tb = report.longrepr.reprtraceback
        except AttributeError:
            return {}
        if not self.want_traceback:
            return {}
        return {
            'traceback': [{
                'path': entry.reprfileloc.path,
                'lineno': entry.reprfileloc.lineno,
                'message': entry.reprfileloc.message,
            } for entry in tb.reprentries],
        }

    def json_summary(self):
        """Return JSON-serializable test result summary."""
        summary = Counter([t['outcome'] for t in self.tests.values()])
        summary['total'] = sum(summary.values())
        return summary

    @pytest.fixture
    def json_metadata(self, request):
        """Fixture to add metadata to the current test item."""
        try:
            metadata = request.node._json_metadata
        except AttributeError:
            metadata = {}
            request.node._json_metadata = metadata
        return metadata


class Hooks:

    def pytest_json_modifyreport(self, json_report):
        """Called after building JSON report and before saving it.

        Plugins can use this hook to modify the report before it's saved.
        """


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

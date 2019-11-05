from __future__ import print_function
from collections import OrderedDict
from contextlib import contextmanager
import json
import logging
import os
import time
import warnings

import pytest

from . import serialize


class JSONReportBase:

    def __init__(self, config=None):
        self._config = config
        self._logger = logging.getLogger()

    def pytest_configure(self, config):
        # When the plugin is used directly from code, it may have been
        # initialized without a config.
        if self._config is None:
            self._config = config
        if not hasattr(config, '_json_report'):
            self._config._json_report = self
        # If the user sets --tb=no, always omit the traceback from the report
        if self._config.option.tbstyle == 'no' and \
           not self._must_omit('traceback'):
            self._config.option.json_report_omit.append('traceback')

    def pytest_addhooks(self, pluginmanager):
        pluginmanager.add_hookspecs(Hooks)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_protocol(self, item, nextitem):
        item._json_report_extra = {}
        yield
        del item._json_report_extra

    @contextmanager
    def _capture_log(self, item, when):
        handler = LoggingHandler()
        self._logger.addHandler(handler)
        try:
            yield
        finally:
            self._logger.removeHandler(handler)
        item._json_report_extra[when]['log'] = handler.records

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_setup(self, item):
        item._json_report_extra['setup'] = {}
        if self._must_omit('log'):
            yield
        else:
            with self._capture_log(item, 'setup'):
                yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        item._json_report_extra['call'] = {}
        if self._must_omit('log'):
            yield
        else:
            with self._capture_log(item, 'call'):
                yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        item._json_report_extra['teardown'] = {}
        if self._must_omit('log'):
            yield
        else:
            with self._capture_log(item, 'teardown'):
                yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        # Hook runtest_makereport to access the item *and* the report
        report = (yield).get_result()
        if not self._must_omit('streams'):
            streams = {key: val for when_, key, val in item._report_sections if
                       when_ == report.when and key in ['stdout', 'stderr']}
            item._json_report_extra[call.when].update(streams)
        for dict_ in self._config.hook.pytest_json_runtest_metadata(item=item,
                                                                    call=call):
            if not dict_:
                continue
            item._json_report_extra.setdefault('metadata', {}).update(dict_)
        self._validate_metadata(item)
        # Attach the JSON details to the report. If this is an xdist worker,
        # the details will be serialized and relayed with the other attributes
        # of the report.
        report._json_report_extra = item._json_report_extra

    @staticmethod
    def _validate_metadata(item):
        """Ensure that `item` has JSON-serializable metadata, otherwise delete
        it."""
        if 'metadata' not in item._json_report_extra:
            return
        try:
            json.dumps(item._json_report_extra['metadata'])
        except (TypeError, OverflowError):
            warnings.warn(
                'Metadata of {} is not JSON-serializable.'.format(item.nodeid))
            del item._json_report_extra['metadata']

    def _must_omit(self, key):
        return key in self._config.option.json_report_omit


class JSONReport(JSONReportBase):
    """The JSON report pytest plugin."""

    def __init__(self, *args, **kwargs):
        JSONReportBase.__init__(self, *args, **kwargs)
        self._start_time = None
        self._json_tests = OrderedDict()
        self._json_collectors = []
        self._json_warnings = []
        # List of terminal summary lines
        self._terminal_summary = []
        self.report = None

    def pytest_sessionstart(self, session):
        self._start_time = time.time()

    def pytest_collectreport(self, report):
        if self._must_omit('collectors'):
            return
        json_result = []
        for item in report.result:
            json_item = serialize.make_collectitem(item)
            item._json_collectitem = json_item
            json_result.append(json_item)
        self._json_collectors.append(serialize.make_collector(report,
                                                              json_result))

    def pytest_deselected(self, items):
        if self._must_omit('collectors'):
            return
        for item in items:
            item._json_collectitem['deselected'] = True

    @pytest.hookimpl(hookwrapper=True)
    def pytest_collection_modifyitems(self, items):
        yield
        if self._must_omit('collectors'):
            return
        for item in items:
            del item._json_collectitem

    def pytest_runtest_logreport(self, report):
        nodeid = report.nodeid
        try:
            json_testitem = self._json_tests[nodeid]
        except KeyError:
            json_testitem = serialize.make_testitem(
                nodeid,
                # report.keywords is a dict (for legacy reasons), but we just
                # need the keys
                None if self._must_omit('keywords') else list(report.keywords),
                report.location,
            )
            self._json_tests[nodeid] = json_testitem
        metadata = report._json_report_extra.get('metadata')
        if metadata:
            json_testitem['metadata'] = metadata
        # Update total test outcome, if necessary. The total outcome can be
        # different from the outcome of the setup/call/teardown stage.
        outcome = self._config.hook.pytest_report_teststatus(
            report=report, config=self._config)[0]
        if outcome not in ['passed', '']:
            json_testitem['outcome'] = outcome
        json_testitem[report.when] = \
            self._config.hook.pytest_json_runtest_stage(report=report)

    @pytest.hookimpl(trylast=True)
    def pytest_json_runtest_stage(self, report):
        if self._must_omit('traceback'):
            traceback = None
        else:
            try:
                traceback = report.longrepr.reprtraceback
            except AttributeError:
                traceback = None
        stage_details = report._json_report_extra[report.when]
        return serialize.make_teststage(
            report,
            stage_details.get('stdout'),
            stage_details.get('stderr'),
            stage_details.get('log'),
            traceback,
        )

    @pytest.hookimpl(tryfirst=True)
    def pytest_sessionfinish(self, session):
        json_report = serialize.make_report(
            created=time.time(),
            duration=time.time() - self._start_time,
            exitcode=session.exitstatus,
            root=str(session.fspath),
            environment=getattr(self._config, '_metadata', {}),
            summary=serialize.make_summary(self._json_tests,
                                           collected=session.testscollected),
        )
        if not self._config.option.json_report_summary:
            if self._json_collectors:
                json_report['collectors'] = self._json_collectors
            json_report['tests'] = list(self._json_tests.values())
            if self._json_warnings:
                json_report['warnings'] = self._json_warnings

        self._config.hook.pytest_json_modifyreport(json_report=json_report)
        # After the session has finished, other scripts may want to use report
        # object directly
        self.report = json_report
        path = self._config.option.json_report_file
        if path:
            self.save_report(path)
        else:
            self._terminal_summary.append('no JSON report written.')

    def save_report(self, path):
        """Save the JSON report to `path`."""
        json_report = self.report
        if json_report is None:
            warnings.warn('No report has been created yet. Nothing saved.')
            return
        # Create path if it doesn't exist
        dirname = os.path.dirname(path)
        if dirname:
            try:
                os.makedirs(dirname)
            # Mimick FileExistsError for py2.7 compatibility
            except OSError as e:
                import errno  # pylint: disable=import-outside-toplevel
                if e.errno != errno.EEXIST:
                    raise
        with open(path, 'w') as f:
            json.dump(
                json_report,
                f,
                default=str,
                indent=self._config.option.json_report_indent,
            )
            self._terminal_summary.append(
                'JSON report written to: %s (%d bytes)' % (path, f.tell()))

    def pytest_warning_captured(self, warning_message, when):
        if self._config is None:
            # If pytest is invoked directly from code, it may try to capture
            # warnings before the config is set.
            return
        if not self._must_omit('warnings'):
            self._json_warnings.append(
                serialize.make_warning(warning_message, when))

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep('-', 'JSON report')
        for line in self._terminal_summary:
            terminalreporter.write_line(line)


class JSONReportWorker(JSONReportBase):

    pass


class LoggingHandler(logging.Handler):

    def __init__(self):
        super(LoggingHandler, self).__init__()
        self.records = []

    def emit(self, record):
        d = dict(record.__dict__)
        d['msg'] = record.getMessage()
        d['args'] = None
        d['exc_info'] = None
        d.pop('message', None)
        self.records.append(d)


class Hooks:

    def pytest_json_modifyreport(self, json_report):
        """Called after building JSON report and before saving it.

        Plugins can use this hook to modify the report before it's saved.
        """

    @pytest.hookspec(firstresult=True)
    def pytest_json_runtest_stage(self, report):
        """Return a dict used as the JSON representation of `report` (the
        `_pytest.runner.TestReport` of the current test stage).

        Called from `pytest_runtest_logreport`. Plugins can use this hook to
        overwrite how the result of a test stage run gets turned into JSON.
        """

    def pytest_json_runtest_metadata(self, item, call):
        """Return a dict which will be added to the current test item's JSON
        metadata.

        Called from `pytest_runtest_makereport`. Plugins can use this hook to
        add metadata based on the current test run.
        """


@pytest.fixture
def json_metadata(request):
    """Fixture to add metadata to the current test item."""
    try:
        return request.node._json_report_extra.setdefault('metadata', {})
    except AttributeError:
        if not request.config.option.json_report:
            # The user didn't request a JSON report, so the plugin didn't
            # prepare a metadata context. We return a dummy dict, so the
            # fixture can be used as expected without causing internal errors.
            return {}
        raise


def pytest_addoption(parser):
    group = parser.getgroup('jsonreport', 'reporting test results as JSON')
    group.addoption(
        '--json-report', default=False, action='store_true',
        help='create JSON report')
    group.addoption(
        '--json-report-file', default='.report.json',
        # The case-insensitive string "none" will make the value None
        type=lambda x: None if x.lower() == 'none' else x,
        help='target path to save JSON report (use "none" to not save the '
        'report)')
    group.addoption(
        '--json-report-omit', default=[], nargs='+', help='list of fields to '
        'omit in the report (choose from: collectors, log, traceback, '
        'streams, warnings, keywords)')
    group.addoption(
        '--json-report-summary', default=False,
        action='store_true', help='only create a summary without per-test '
        'details')
    group.addoption(
        '--json-report-indent', type=int, help='pretty-print JSON with '
        'specified indentation level')


def pytest_configure(config):
    if not config.option.json_report:
        return
    if hasattr(config, 'workerinput'):
        Plugin = JSONReportWorker
    else:
        Plugin = JSONReport
    plugin = Plugin(config)
    config._json_report = plugin
    config.pluginmanager.register(plugin)


def pytest_unconfigure(config):
    plugin = getattr(config, '_json_report', None)
    if plugin is not None:
        del config._json_report
        config.pluginmanager.unregister(plugin)

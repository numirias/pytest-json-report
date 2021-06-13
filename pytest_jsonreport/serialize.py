"""Functions for making test data JSON-serializable.

"""
from collections import Counter
import json


def serializable(obj):
    """Return whether `obj` is JSON-serializable."""
    try:
        json.dumps(obj)
    except (TypeError, OverflowError):
        return False
    return True


def make_collector(report, result):
    """Return JSON-serializable collector node."""
    collector = {
        'nodeid': report.nodeid,
        # This is the outcome of the collection, not the test outcome
        'outcome': report.outcome,
        'result': result,
    }
    if report.longrepr:
        # The collection report doesn't provide crash details, so we can only
        # add the message, but no traceback etc.
        collector['longrepr'] = str(report.longrepr)
    return collector


def make_collectitem(item):
    """Return JSON-serializable collection item."""
    json_item = {
        'nodeid': item.nodeid,
        'type': item.__class__.__name__,
    }
    try:
        location = item.location
    except AttributeError:
        pass
    else:
        json_item['lineno'] = location[1]
    return json_item


def make_testitem(nodeid, keywords, location):
    """Return JSON-serializable test item."""
    item = {
        'nodeid': nodeid,
        'lineno': location[1],
        # The outcome will be overridden in case of failure
        'outcome': 'passed',
    }
    if keywords:
        item['keywords'] = keywords
    return item


def make_teststage(report, stdout, stderr, log, omit_traceback):
    """Return JSON-serializable test stage (setup/call/teardown)."""
    stage = {
        'duration': report.duration,
        'outcome': report.outcome,
    }
    crash = getattr(report.longrepr, 'reprcrash', None)
    if crash is not None:
        stage['crash'] = make_fileloc(crash)
        if not omit_traceback:
            try:
                stage['traceback'] = [make_fileloc(x.reprfileloc) for x in
                                      report.longrepr.reprtraceback.reprentries]
            except AttributeError:
                # Happens if no detailed tb entries are available (e.g. due to
                # `--tb=native`, see `_pytest._code.code.ReprTracebackNative`).
                # Then we can't provide any tb info beyond the raw error text
                # in `longrepr`, so just pass quietly.
                pass
    if stdout:
        stage['stdout'] = stdout
    if stderr:
        stage['stderr'] = stderr
    if log:
        stage['log'] = log
    # Error representation string (attr is computed property, so get only once)
    longrepr = report.longreprtext
    if longrepr:
        stage['longrepr'] = longrepr
    return stage


def make_fileloc(loc):
    """Return JSON-serializable file location representation.

    See `_pytest._code.code.ReprFileLocation`.
    """
    return {
        'path': loc.path,
        'lineno': loc.lineno,
        'message': loc.message,
    }


def make_summary(tests, **kwargs):
    """Return JSON-serializable test result summary."""
    summary = Counter([t['outcome'] for t in tests.values()])
    summary['total'] = sum(summary.values())
    summary.update(kwargs)
    return summary


def make_warning(warning_message, when):
    # `warning_message` is a stdlib warnings.WarningMessage object
    return {
        'message': str(warning_message.message),
        'category': warning_message.category.__name__,
        'when': when,
        'filename': warning_message.filename,
        'lineno': warning_message.lineno
    }


def make_report(**kwargs):
    return dict(kwargs)

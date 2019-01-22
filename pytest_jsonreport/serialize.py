"""Functions for making test data JSON-serializable.

"""
from collections import Counter


def make_collector(report):
    """Return JSON-serializable collector node."""
    result = []
    for item in report.result:
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
        result.append(json_item)

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


def make_teststage(report, stdout, stderr, log, traceback):
    """Return JSON-serializable test stage (setup/call/teardown)."""
    stage = {
        'duration': report.duration,
        'outcome': report.outcome,
    }
    stage.update(make_crash(report))
    if traceback:
        stage['traceback'] = make_traceback(traceback)
    if stdout:
        stage['stdout'] = stdout
    if stderr:
        stage['stderr'] = stderr
    if log:
        stage['log'] = log
    if report.longreprtext:
        stage['longrepr'] = report.longreprtext
    return stage


def make_crash(report):
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


def make_traceback(traceback):
    """Return JSON-serializable traceback details."""
    return [{
        'path': entry.reprfileloc.path,
        'lineno': entry.reprfileloc.lineno,
        'message': entry.reprfileloc.message,
    } for entry in traceback.reprentries]


def make_summary(tests):
    """Return JSON-serializable test result summary."""
    summary = Counter([t['outcome'] for t in tests.values()])
    summary['total'] = sum(summary.values())
    return summary


def make_warning(warning_message, when):
    # warning_message is a warnings.WarningMessage object
    return {
        'message': str(warning_message.message),
        'when': when,
        'filename': warning_message.filename,
        'lineno': warning_message.lineno
    }


def make_report(**kwargs):
    return dict(kwargs)

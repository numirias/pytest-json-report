# Pytest JSON Report

[![Build Status](https://travis-ci.org/numirias/pytest-json-report.svg?branch=master)](https://travis-ci.org/numirias/pytest-json-report)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)

This pytest plugin creates JSON test reports, so that the results can be processed by other applications.

It can report a summary, test details, captured output, logs, exception tracebacks and more. Additionally, you can use the available fixtures and hooks to [add metadata](#metadata) and customize the report as you like.

## Installation

```
pip install pytest-json-report --upgrade 
```
## Usage

Just run pytest with `--json-report`. The report is saved in `.report.json` by default.

```
$ pytest -v --json-report
$ cat .report.json
{"created": 1518371686.7981803, ... "tests":[{"nodeid": "test_foo.py", "outcome": "passed", ...}, ...]}
```
Available options:

| Option | Description |
| --- | --- |
| `--json-report` | Create JSON report |
| `--json-report-file=JSON_REPORT_FILE` | Target path to save JSON report |
| `--json-report-no-traceback` | Don't include tracebacks in JSON report |
| `--json-report-no-streams` | Don't include stdout/stderr output in JSON report |
| `--json-report-summary` |  Just create a summary without per-test details |
| `--json-report-indent=JSON_REPORT_INDENT` |  Pretty-print JSON with specified indentation level |


If your report files are getting uncomfortably large, try `--json-report-no-streams` or `--json-report-summary`.

## Format

The JSON report contains metadata of the session, a summary, collectors, tests and warnings. You can find a sample report in [`sample_report.json`](sample_report.json).

| Key | Description |
| --- | --- |
| `created` | Report creation date. (Unix time) |
| `duration` | Session duration in seconds. |
| `exitcode` | Process exit code as listed [in the pytest docs](https://docs.pytest.org/en/latest/usage.html#possible-exit-codes). The exit code is a quick way to tell if any tests failed, an internal error occurred, etc. |
| `root` | Absolute root path from which the session was started. |
| `environment` | [Environment](#environment) entry. |
| `summary` | [Summary](#summary) entry. |
| `collectors` | [Collectors](#collectors) entry. (absent if `--json-report-summary`)  |
| `tests` | [Tests](#tests) entry. (absent if `--json-report-summary`)  |
| `warnings` | [Warnings](#warnings) entry. (absent if `--json-report-summary` or if no warnings occurred)  |

#### Example

```python
{
    "created": 1518371686.7981803,
    "duration": 0.1235666275024414,
    "exitcode": 1,
    "root": "/path/to/tests",
    "environment": ENVIRONMENT,
    "summary": SUMMARY,
    "collectors": COLLECTORS,
    "tests": TESTS,
    "warnings": WARNINGS,
}
```

### Summary

Number of outcomes per category and the total number of test items.

| Key | Description |
| --- | --- |
| *`outcome`* | Number of tests with that outcome. (absent if number is 0) |
|  `total` | Total number of tests. |

#### Example

```python
{
    "passed": 2,
    "failed": 3,
    "xfailed": 1,
    "xpassed": 1,
    "error": 2,
    "skipped": 1,
    "total": 10
}
```

### Environment

The environment section is provided by [pytest-metadata](https://github.com/pytest-dev/pytest-metadata). All metadata given by that plugin will be added here, so you need to make sure it is JSON-serializable.

#### Example

```python
{
    "Python": "3.6.4",
    "Platform": "Linux-4.56.78-9-ARCH-x86_64-with-arch",
    "Packages": {
        "pytest": "3.4.0",
        "py": "1.5.2",
        "pluggy": "0.6.0"
    },
    "Plugins": {
        "json-report": "0.4.1",
        "xdist": "1.22.0",
        "metadata": "1.5.1",
        "forked": "0.2",
        "cov": "2.5.1"
    },
    "foo": "bar", # Custom metadata entry passed via pytest-metadata
}
```

### Collectors

A list of collector nodes.

| Key | Description |
| --- | --- |
| `nodeid` | ID of the test node. ([See docs](https://docs.pytest.org/en/latest/example/markers.html#node-id)) The root node has an empty node ID. |
| `outcome` | Outcome of the collection. (Not the test outcome!) |
| `children` | Children of the collector node which are either other collectors or test nodes. |
| `longrepr` | Representation of the error. (absent if no error occurred) |

#### Example

```python
[
    {
        "nodeid": "",
        "outcome": "passed",
        "children": [
            {
                "nodeid": "test_foo.py",
                "type": "Module"
            }
        ]
    },
    {
        "nodeid": "test_foo.py",
        "outcome": "passed",
        "children": [
            {
                "nodeid": "test_foo.py::test_pass",
                "type": "Function",
                "path": "test_foo.py",
                "lineno": 24,
                "domain": "test_pass"
            },
            ...
        ]
    },
    {
        "nodeid": "test_bar.py",
        "outcome": "failed",
        "children": [],
        "longrepr": "/usr/lib/python3.6 ... invalid syntax"
    },
    ...
]
```

### Tests

A list of test nodes. Each completed test stage produces a stage object (`setup`, `call`, `teardown`) with its own `outcome`.

| Key | Description |
| --- | --- |
| `nodeid` | ID of the test node. |
| `path` | Relative path to the test file. |
| `lineno` | Line number where the test starts. |
| `domain` | Name of the test item. |
| `keywords` | List of keywords and markers associated with the test. |
| `outcome` | Outcome of the test run. |
| `{setup, call, teardown}` | [Test stage](#test-stage) entry. To find the error in a failed test you need to check all stages. (absent if stage didn't run) |
| `metadata` | [Metadata](#metadata) item. |

#### Example

```python
[
    {
        "nodeid": "test_foo.py::test_fail",
        "path": "test_foo.py",
        "lineno": 50,
        "domain": "test_fail",
        "keywords": [
            "test_fail",
            "test_foo.py",
            "test_foo0"
        ],
        "outcome": "failed",
        "setup": TEST_STAGE,
        "call": TEST_STAGE,
        "teardown": TEST_STAGE,
        "metadata": {
            "foo": "bar",
        }
    },
    ...
]
```


### Test stage

A test stage item.

| Key | Description |
| --- | --- |
| `duration` | Duration of the test stage in seconds. |
| `outcome` | Outcome of the test stage. (can be different from the overall test outcome) |
| `crash` | Crash entry. (absent if no error occurred) |
| `traceback` | List of traceback entries. (absent if no error occurred) |
| `stdout` | Standard output. (absent if no stdout output or `--json-report-no-streams`) |
| `stderr` | Standard error. (absent if no stderr output or `--json-report-no-streams`) |
| `log` | [Log](#log) entry. |
| `longrepr` | Representation of the error. (absent if no error occurred) |

#### Example

```python
{
    "duration": 0.00018835067749023438,
    "outcome": "failed",
    "crash": {
        "path": "/path/to/tests/test_foo.py",
        "lineno": 54,
        "message": "TypeError: unsupported operand type(s) for -: 'int' and 'NoneType'"
    },
    "traceback": [
        {
            "path": "test_foo.py",
            "lineno": 65,
            "message": ""
        },
        {
            "path": "test_foo.py",
            "lineno": 63,
            "message": "in foo"
        },
        {
            "path": "test_foo.py",
            "lineno": 63,
            "message": "in <listcomp>"
        },
        {
            "path": "test_foo.py",
            "lineno": 54,
            "message": "TypeError"
        }
    ],
    "stdout": "foo\nbar\n",
    "stderr": "baz\n",
    "log": LOG,
    "longrepr": "def test_fail_nested():\n ..."
}
```

### Log

A list of log records. The fields of a log record are the [`logging.LogRecord` attributes](https://docs.python.org/3/library/logging.html#logrecord-attributes), with the exception that the fields `exc_info` and `args` are always empty and `msg` contains the formatted log message.

You can apply [`logging.makeLogRecord()`](https://docs.python.org/3/library/logging.html#logging.makeLogRecord)  on a log record to convert it back to a `logging.LogRecord` object.

#### Example

```python
[
    {
        "name": "root",
        "msg": "This is a warning.",
        "args": null,
        "levelname": "WARNING",
        "levelno": 30,
        "pathname": "/path/to/tests/test_foo.py",
        "filename": "test_foo.py",
        "module": "test_foo",
        "exc_info": null,
        "exc_text": null,
        "stack_info": null,
        "lineno": 8,
        "funcName": "foo",
        "created": 1519772464.291738,
        "msecs": 291.73803329467773,
        "relativeCreated": 332.90839195251465,
        "thread": 140671803118912,
        "threadName": "MainThread",
        "processName": "MainProcess",
        "process": 31481
    },
    ...
]
```


### Warnings

A list of warnings that occurred during the session. (See the [pytest docs on warnings](https://docs.pytest.org/en/latest/warnings.html).)

| Key | Description |
| --- | --- |
| `code` | Warning code. |
| `path` | Absolute path to the associated file. |
| `nodeid` | Associated node ID. |
| `message` | Warning message. |

#### Example

```python
[
    {
        "code": "C1",
        "path": "/path/to/tests/test_foo.py",
        "nodeid": "test_foo.py::TestFoo",
        "message": "cannot collect test class 'TestFoo' because it has a __init__ constructor"
    }
]
```

## Metadata

You can add metadata to a test item by using the `json_metadata` test fixture:

```python
def test_something(json_metadata):
    json_metadata['foo'] = {"some": "thing"}
```

If the metadata isn't JSON-serializable, it will be converted to a string.

Also, you could add metadata using [pytest-metadata's `--metadata` switch](https://github.com/pytest-dev/pytest-metadata#additional-metadata) which will add metadata to the report's `environment` section, but not to a specific test item.

## Accessing the report

If you wish, you can modify the entire report before it's saved by using the `pytest_json_modifyreport` hook.

Just add the hook to your `conftest.py`, e.g.:

```python
def pytest_json_modifyreport(json_report):
    # Add a key to the report
    json_report['foo'] = 'bar'
    # Delete the summary from the report
    del json_report['summary']
```

After `pytest_sessionfinish`, the report object is available via `config._json_report`, so you could also access it using a standard hook (although this isn't recommended). E.g.:

```python
def pytest_sessionfinish(session):
    code = session.config._json_report.report['exitcode']
    ...
```

## Direct invocation

You can also use the plugin when invoking `pytest.main()` directly from code:

```python
import pytest
from pytest_jsonreport.plugin import JSONReport

plugin = JSONReport()
pytest.main(['test_foo.py'], plugins=[plugin])
print(plugin.report)
```

## Related tools

- [pytest-json](https://github.com/mattcl/pytest-json) has some great features but appears to be unmaintained. I borrowed some ideas and test cases from there.

- [tox has a swtich](http://tox.readthedocs.io/en/latest/example/result.html) to create a JSON report including a test result summary. However, it just provides the overall outcome without any per-test details.

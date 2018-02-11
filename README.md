# Pytest JSON Report

[![Build Status](https://travis-ci.org/numirias/pytest-json-report.svg?branch=master)](https://travis-ci.org/numirias/pytest-json-report)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)

This pytest plugin saves test reports to JSON files, so that the results can be processed by other applications.

You can have a large report including captured output and exception tracebacks, or just a summary, as you wish. Also, you can add metadata by using a fixture or implement hooks to modify the entire report.

## Installation

```
pip install pytest-json-report --upgrade 
```
## Usage

Just run pytest with `--json-report`. (The report is saved in `.report.json` by default.)

```
$ pytest -v --json-report
$ cat .report.json
{"created": 1518371686.7981803, ... "tests":[{"nodeid": "test_foo.py", "outcome": "passed", ...}, ...]}
```
Available switches:

```
$ pytest -h
...
reporting test results as JSON:
  --json-report         create JSON report
  --json-report-file=JSON_REPORT_FILE
                        target path to save JSON report
  --json-report-no-traceback
                        don't include tracebacks in JSON report
  --json-report-no-streams
                        don't include stdout/stderr output in JSON report
  --json-report-summary
                        just create a summary without per-test details
...
[pytest] ini-options in the first pytest.ini|tox.ini|setup.cfg file found:
  json_report_file (string) target file to save JSON report
...
```
If your report files are getting uncomfortably large, try `--json-report-no-streams` or `--json-report-summary`.

## Format

The JSON report contains metadata of the session, a summary, collectors, tests and warnings:

```python
{
    "created": 1518371686.7981803, # Creation date timestamp
    "duration": 0.1235666275024414, # Session duration in seconds
    "exitcode": 1, # Exit code as listed in https://docs.pytest.org/en/latest/usage.html#possible-exit-codes
    "root": "/tmp/path/to/tests",
    "environment": ENVIRONMENT,
    "summary": SUMMARY,
    "collectors": COLLECTORS,
    "tests": TESTS,
    "warnings": WARNINGS,
}
```

### Summary

The summary section lists the number of outcomes per category and the total number of test items.

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
    "foo": "bar", # Metadata provided by pytest-metadata
}
```

### Collectors

Collectors are a list of nodes. Nodes in `children` are either test items or other collectors. When a collection fails (e.g. through a syntax error or an exception in the test itself), `longrepr` provides the error message. Note that `outcome` is not the outcome of a test run, but indicates if the collection was successful.

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

Tests are a list of test run items. Each completed test stage produces a stage object (`setup`, `call`, `teardown`) with its own `outcome` (which may be different from the overall test outcome). The output of the standard streams (`stdout`, `stderr`), the error message (`longrepr`) and the error details (`crash`, `traceback`) are available as keys on their respective stage.

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
        "setup": {
            "duration": 0.00014090538024902344,
            "outcome": "passed"
        },
        "call": {
            "duration": 0.00018835067749023438,
            "outcome": "failed",
            "crash": {
                "path": "/tmp/path/to/tests/test_foo.py",
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
            "longrepr": "def test_fail_nested():\n ..."
        },
        "teardown": {
            "duration": 0.0001399517059326172,
            "outcome": "passed"
        }
        "metadata": {
            "foo": "bar",
        }
    },
    ...
]
```

### Warnings

The warnings section contains a list of warnings that occurred during the session. (See the [pytest docs on warnings](https://docs.pytest.org/en/latest/warnings.html).)

```python
[
    {
        "code": "C1",
        "path": "/tmp/path/to/tests/test_foo.py",
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

You can also access the report object using a standard hook (although this isn't recommended). E.g.:

```python
def pytest_sessionfinish(session):
    code = session.config._json_report.report['exitcode']
    ...
```


## Related tools

- [pytest-json](https://github.com/mattcl/pytest-json) has some great features but appears to be unmaintained. I borrowed some ideas and test cases from there.

- [tox has a swtich](http://tox.readthedocs.io/en/latest/example/result.html) to create a JSON report including a test result summary. However, it just provides the overall outcome without any per-test details.

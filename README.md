# Pytest JSON Report

[![Build Status](https://travis-ci.org/numirias/pytest-json-report.svg?branch=master)](https://travis-ci.org/numirias/pytest-json-report)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)

This pytest plugin saves test reports to JSON files so that the results can be processed by other applications.

## Installation

```
pip install pytest-json-report --upgrade 
```
## Usage

Usage example:

```
$ pytest -v --json-report --json-report-file results.json tests/
$ cat results.json
[{"path": "tests/test_app.py", "line": 17, "domain": "TestMain.test_main", ...}, {...}, ...]
```
By default, the report is saved in `.report.json`. The plugin provides these switches:

```
$ pytest -h
...
reporting test results as JSON:
  --json-report         create JSON report
  --json-report-file=JSON_REPORT_FILE
                        target file to save JSON report
...
```

## Format

The JSON report is a list of test result items (dicts):

```python
[
    {
        'path': 'tests/test_foo.py',
        'line': 123,
        'domain': 'test_some_foo',
        'outcome': 'passed',
        'when': 'call',
        'nodeid': 'tests/test_foo.py::test_some_foo',
        'duration': 0.00016',
        'keywords': {'test_some_foo': 1, ...},
        'longrepr': '... assert False ...',
    },
    ...
]
```
See the pytest documentation on [`_pytest.runner.TestReport`](https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.runner.TestReport) for details on what the individual keys mean. Note that `(path, line, domain)` is the `TestReport.location` tuple.

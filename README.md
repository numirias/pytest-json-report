# Pytest JSON Report

[![Build Status](https://travis-ci.org/numirias/pytest-json-report.svg?branch=master)](https://travis-ci.org/numirias/pytest-json-report)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)

This pytest plugin can report test results to JSON files so that they can be processed by other applications.

## Installation

```
pip install pytest-json-report --upgrade 
```
## Usage

```
$ pytest -h
...
reporting test results as JSON:
  --json-report         create JSON report
  --json-report-file=JSON_REPORT_FILE
                        target file to save JSON report
```

E.g.:

```
$ pytest -v --json-report --json-report-file results.json tests/
```

## Format

The JSON data is a list of test result items:

```python
item = {
    'path': 'tests/test_foo.py',
    'line': 123,
    'domain': 'test_some_foo',
    'outcome': 'passed',
    'when': 'call',
    'nodeid': 'tests/test_foo.py::test_some_foo',
}
```
See the documentation for [`_pytest.runner.TestReport`](https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.runner.TestReport) for details on what the keys mean. Also note that `(path, line, domain)` is the `TestReport.location` tuple.

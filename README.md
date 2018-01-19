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
{"created": "...", ..., "tests":[{"nodeid": "test_foo.py", "outcome": "passed", ...}, {...}, ...]}
```
By default, the report is saved in `.report.json`. Also, these switches are available:

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

The JSON report contains metadata and an array of test objects. E.g.:

```python
{
    "created": "2018-01-19T20:58:06.296891+02:00",
    "duration": 0.02450704574584961,
    "python": "3.6.3",
    "pytest": "3.3.2",
    "platform": "Linux-1.23.5-1-ARCH-x86_64-with-arch",
    "tests": [
        {
            "nodeid": "test_report_tests.py::test_fail_with_fixture",
            "path": "test_report_tests.py",
            "line": 18,
            "domain": "test_fail_with_fixture",
            "outcome": "failed",
            "keywords": {
                "test_report_tests0": 1,
                "test_fail_with_fixture": 1,
                "test_report_tests.py": 1
            },
            "setup": {
                "duration": 0.00031757354736328125,
                "outcome": "passed",
                "longrepr": null
            },
            "call": {
                "duration": 0.0002713203430175781,
                "outcome": "failed",
                "longrepr": "setup_teardown_fixture = None\n ..."
            },
            "teardown": {
                "duration": 0.00019168853759765625,
                "outcome": "passed",
                "longrepr": null
            }
        },
        ...
    ]
}

```
See the pytest documentation on [`_pytest.runner.TestReport`](https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.runner.TestReport) for details on what the individual keys of the test objects mean. Note that `(path, line, domain)` is the `TestReport.location` tuple.

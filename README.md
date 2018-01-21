# Pytest JSON Report

[![Build Status](https://travis-ci.org/numirias/pytest-json-report.svg?branch=master)](https://travis-ci.org/numirias/pytest-json-report)
[![PyPI Version](https://img.shields.io/pypi/v/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)
[![Python Versions](https://img.shields.io/pypi/pyversions/pytest-json-report.svg)](https://pypi.python.org/pypi/pytest-json-report)

This pytest plugin saves test reports to JSON files, so that the results can be processed by other applications.

You can have a large report including captured output and exception tracebacks, or just a summary, as you wish.

## Installation

```
pip install pytest-json-report --upgrade 
```
## Usage

Just run pytest with `--json-report`. (The report is saved in `.report.json` by default.)

```
$ pytest -v --json-report
$ cat .report.json
{"created": "2018-01-19T20:58:06.296891+02:00", ... "tests":[{"nodeid": "test_foo.py", "outcome": "passed", ...}, ...]}
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

The JSON report contains metadata of the session, a summary and an array of test result objects:

```python
{
    "created": "2018-01-19T20:58:06.296891+02:00",
    "duration": 0.02450704574584961,
    "python": "3.6.3",
    "pytest": "3.3.2",
    "platform": "Linux-1.23.5-1-ARCH-x86_64-with-arch",
    "summary": {
        "passed": 1,
        "failed": 2,
        "xfailed": 1,
        "xpassed": 1,
        "error": 2,
        "skipped": 1,
        "total": 8
    },
    "tests": [
        {
            "nodeid": "test_foo.py::test_bar",
            "path": "test_foo.py",
            "lineno": 18,
            "domain": "test_bar",
            "outcome": "failed",
            "keywords": {
                "test_bar": 1,
                ...
            },
            "setup": {
                "duration": 0.00031757354736328125,
                "outcome": "passed",
            },
            "call": {
                "duration": 0.0002713203430175781,
                "outcome": "failed",
                "longrepr": "def bar():\n ..."
                "stdout": "foo\nbar\n",
                "stderr": "baz\n",
                "crash": {
                    "path": "test_foo.py.py",
                    "lineno": 54,
                    "info": "TypeError: 'int' object is not subscriptable"
                },
                "traceback": [
                    {
                        "path": "test_foo.py",
                        "lineno": 65,
                        "info": ""
                    },
                    {
                        "path": "test_foo.py",
                        "lineno": 63,
                        "info": "in foo"
                    },
                    {
                        "path": "test_foo.py",
                        "lineno": 63,
                        "info": "in <listcomp>"
                    },
                    {
                        "path": "test_foo.py",
                        "lineno": 59,
                        "info": "in bar"
                    },
                    {
                        "path": "test_foo.py",
                        "lineno": 54,
                        "info": "TypeError"
                    }
                ]
            },
            "teardown": {
                "duration": 0.00019168853759765625,
                "outcome": "passed",
            }
        },
        ...
    ]
}

```
See the pytest docs on [`_pytest.runner.TestReport`](https://docs.pytest.org/en/latest/writing_plugins.html#_pytest.runner.TestReport) for details on what the keys of the test result objects mean. Note that `(path, lineno, domain)` is the `TestReport.location` tuple.

Also be aware that output and exceptions don't always occur in the `call` stage. That is, if you want to check where a test failed or collect all stdout output, you should check`setup` and `teardown`, too.

## Similar tools

- [pytest-json](https://github.com/mattcl/pytest-json) has some neat features but appears to be unmaintained. I borrowed some features and test cases from there.

- [tox has a swtich](http://tox.readthedocs.io/en/latest/example/result.html) to create a JSON report including a test result summary. However, it just provides the overall outcome without test details.

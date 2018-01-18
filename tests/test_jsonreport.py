import json
import pytest


@pytest.fixture
def jr_testdir(testdir):
    testdir.makepyfile("""
        def test_foo():
            assert True
        def test_bar():
            assert False
        def test_baz():
            assert False
    """)
    return testdir


def test_arguments_in_help(jr_testdir):
    res = jr_testdir.runpytest('--help')
    res.stdout.fnmatch_lines(['*json-report*'])


def test_no_jsonreport(jr_testdir):
    jr_testdir.runpytest()
    assert not (jr_testdir.tmpdir / '.report.json').exists()


def test_jsonreport_create_report(jr_testdir):
    jr_testdir.runpytest('--json-report')
    assert (jr_testdir.tmpdir / '.report.json').exists()


def test_jsonreport_create_report_with_custom_file(jr_testdir):
    jr_testdir.runpytest('--json-report', '--json-report-file=foo.js')
    assert (jr_testdir.tmpdir / 'foo.js').exists()


def test_jsonreport_report_file(jr_testdir):
    jr_testdir.runpytest('--json-report')
    with open(str(jr_testdir.tmpdir / '.report.json')) as f:
        data = json.load(f)

    assert len(data) == 3
    passed = next(x for x in data if x['outcome'] == 'passed')
    failed = next(x for x in data
                  if x['outcome'] == 'failed' and x['domain'] == 'test_baz')
    assert passed['line'] == 0
    assert passed['domain'] == 'test_foo'
    assert failed['line'] == 4
    assert 'assert False' in failed['longrepr']

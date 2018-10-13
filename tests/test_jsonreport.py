import json
import logging
import pytest

from pytest_jsonreport.plugin import JSONReport


# Some test cases borrowed from github.com/mattcl/pytest-json
FILE = """
import sys
import pytest


@pytest.fixture
def setup_teardown_fixture(request):
    print('setup')
    print('setuperr', file=sys.stderr)
    def fn():
        print('teardown')
        print('teardownerr', file=sys.stderr)
    request.addfinalizer(fn)

@pytest.fixture
def fail_setup_fixture(request):
    assert False

@pytest.fixture
def fail_teardown_fixture(request):
    def fn():
        assert False
    request.addfinalizer(fn)


def test_pass():
    assert True

def test_fail_with_fixture(setup_teardown_fixture):
    print('call')
    print('callerr', file=sys.stderr)
    assert False

@pytest.mark.xfail(reason='testing xfail')
def test_xfail():
    assert False

@pytest.mark.xfail(reason='testing xfail')
def test_xfail_but_passing():
    assert True

def test_fail_during_setup(fail_setup_fixture):
    assert True

def test_fail_during_teardown(fail_teardown_fixture):
    assert True

@pytest.mark.skipif(True, reason='testing skip')
def test_skip():
    assert False

def test_fail_nested():
    def baz(o=1):
        c = 3
        return 2 - c - None
    def bar(m, n=5):
        b = 2
        print(m)
        print('bar')
        return baz()
    def foo():
        a = 1
        print('foo')
        v = [bar(x) for x in range(3)]
        return v
    foo()

@pytest.mark.parametrize('x', [1, 2])
def test_parametrized(x):
    assert x == 1
"""


@pytest.fixture
def misc_testdir(testdir):
    testdir.makepyfile(FILE)
    return testdir


@pytest.fixture
def json_data(make_json):
    return make_json()


@pytest.fixture
def tests(json_data):
    return make_tests(json_data)


def make_tests(json_data):
    return {test['domain'][5:]: test for test in json_data['tests']}


@pytest.fixture
def make_json(testdir):
    def func(content=FILE, args=['-vv', '--json-report'], path='.report.json'):
        testdir.makepyfile(content)
        testdir.runpytest(*args)
        with open(str(testdir.tmpdir / path)) as f:
            data = json.load(f)
        return data
    return func


def test_arguments_in_help(misc_testdir):
    res = misc_testdir.runpytest('--help')
    res.stdout.fnmatch_lines([
        '*json-report*',
        '*json-report-file*',
        '*json_report_file*',
    ])


def test_no_report(misc_testdir):
    misc_testdir.runpytest()
    assert not (misc_testdir.tmpdir / '.report.json').exists()


def test_create_report(misc_testdir):
    misc_testdir.runpytest('--json-report')
    assert (misc_testdir.tmpdir / '.report.json').exists()


def test_create_report_file_from_arg(misc_testdir):
    misc_testdir.runpytest('--json-report', '--json-report-file=arg.json')
    assert (misc_testdir.tmpdir / 'arg.json').exists()


def test_create_report_file_from_ini(misc_testdir):
    misc_testdir.makeini("""
        [pytest]
        json_report_file = ini.json
    """)
    misc_testdir.runpytest('--json-report')
    assert (misc_testdir.tmpdir / 'ini.json').exists()


def test_create_report_file_priority(misc_testdir):
    misc_testdir.makeini("""
        [pytest]
        json_report_file = ini.json
    """)
    misc_testdir.runpytest('--json-report', '--json-report-file=arg.json')
    assert (misc_testdir.tmpdir / 'arg.json').exists()


def test_report_keys(make_json):
    data = make_json()
    assert set(data) == set([
        'created', 'duration', 'environment', 'collectors', 'tests', 'summary',
        'root', 'exitcode'
    ])
    assert isinstance(data['created'], float)
    assert isinstance(data['duration'], float)
    assert data['root'].startswith('/')
    assert data['exitcode'] == 1


def test_report_collectors(make_json):
    collectors = make_json()['collectors']
    assert len(collectors) == 2
    assert all(c['outcome'] == 'passed' for c in collectors)
    assert collectors[0] == {
        'nodeid': '',
        'outcome': 'passed',
        'children': [
            {
                'nodeid': 'test_report_collectors.py',
                'type': 'Module',
            }
        ]
    }
    assert {
        'nodeid': 'test_report_collectors.py::test_pass',
        'type': 'Function',
        'path': 'test_report_collectors.py',
        'lineno': 24,
        'domain': 'test_pass',
    } in collectors[1]['children']


def test_report_failed_collector(make_json):
    data = make_json("""
        syntax error
        def test_foo():
            assert True
    """)
    collectors = data['collectors']
    assert data['tests'] == []
    assert collectors[0]['outcome'] == 'passed'
    assert collectors[1]['outcome'] == 'failed'
    assert collectors[1]['children'] == []
    assert 'longrepr' in collectors[1]


def test_report_failed_collector2(make_json):
    data = make_json("""
        import nonexistent
        def test_foo():
            pass
    """)
    collectors = data['collectors']
    assert collectors[1]['longrepr'].startswith('ImportError')


def test_report_item_keys(tests):
    assert set(tests['pass']) == set(['nodeid', 'path', 'lineno', 'domain',
                                      'outcome', 'keywords', 'setup', 'call',
                                      'teardown'])


def test_report_outcomes(tests):
    assert len(tests) == 10
    assert tests['pass']['outcome'] == 'passed'
    assert tests['fail_with_fixture']['outcome'] == 'failed'
    assert tests['xfail']['outcome'] == 'xfailed'
    assert tests['xfail_but_passing']['outcome'] == 'xpassed'
    assert tests['fail_during_setup']['outcome'] == 'error'
    assert tests['fail_during_teardown']['outcome'] == 'error'
    assert tests['skip']['outcome'] == 'skipped'


def test_report_summary(make_json):
    assert make_json()['summary'] == {
        'total': 10,
        'passed': 2,
        'failed': 3,
        'skipped': 1,
        'xpassed': 1,
        'xfailed': 1,
        'error': 2,
    }


def test_report_longrepr(tests):
    assert 'assert False' in tests['fail_with_fixture']['call']['longrepr']


def test_report_crash_and_traceback(tests):
    assert 'traceback' not in tests['pass']['call']
    call = tests['fail_nested']['call']
    assert call['crash']['path'].endswith('test_report_crash_and_traceback.py')
    assert call['crash']['lineno'] == 54
    assert call['crash']['message'].startswith('TypeError: unsupported ')
    assert call['traceback'] == [
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 65,
            'message': ''
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 63,
            'message': 'in foo'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 63,
            'message': 'in <listcomp>'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 59,
            'message': 'in bar'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 54,
            'message': 'TypeError'
        }
    ]


def test_no_traceback(make_json):
    data = make_json(FILE, ['--json-report', '--json-report-no-traceback'])
    tests_ = make_tests(data)
    assert 'traceback' not in tests_['fail_nested']['call']


def test_pytest_no_traceback(make_json):
    data = make_json(FILE, ['--json-report', '--tb=no'])
    tests_ = make_tests(data)
    assert 'traceback' not in tests_['fail_nested']['call']


def test_no_streams(make_json):
    data = make_json(FILE, ['--json-report', '--json-report-no-streams'])
    call = make_tests(data)['fail_with_fixture']['call']
    assert 'stdout' not in call
    assert 'stderr' not in call


def test_no_logs(make_json):
    data = make_json("""
        import logging
        def test_foo():
            logging.error('log error')
    """, ['--json-report'])
    assert 'log' in data['tests'][0]['call']
    data = make_json("""
        import logging
        def test_foo():
            logging.error('log error')
    """, ['--json-report', '--json-report-no-logs'])
    assert 'log' not in data['tests'][0]['call']


def test_summary_only(make_json):
    data = make_json(FILE, ['--json-report', '--json-report-summary'])
    assert 'summary' in data
    assert 'tests' not in data
    assert 'collectors' not in data
    assert 'warnings' not in data


def test_report_streams(tests):
    test = tests['fail_with_fixture']
    assert test['setup']['stdout'] == 'setup\n'
    assert test['setup']['stderr'] == 'setuperr\n'
    assert test['call']['stdout'] == 'call\n'
    assert test['call']['stderr'] == 'callerr\n'
    assert test['teardown']['stdout'] == 'teardown\n'
    assert test['teardown']['stderr'] == 'teardownerr\n'
    assert 'stdout' not in tests['pass']['call']
    assert 'stderr' not in tests['pass']['call']


def test_json_metadata(make_json):
    data = make_json("""
        def test_metadata1(json_metadata):
            json_metadata['x'] = 'foo'
            json_metadata['y'] = [1, {'a': 2}]

        def test_metadata2(json_metadata):
            json_metadata['z'] = 1
            assert False

        def test_unused_metadata(json_metadata):
            assert True

        def test_empty_metadata(json_metadata):
            json_metadata.update({})

        def test_unserializable_metadata(json_metadata):
            json_metadata['a'] = object()

    """)
    tests_ = make_tests(data)
    assert tests_['metadata1']['metadata'] == {'x': 'foo', 'y': [1, {'a': 2}]}
    assert tests_['metadata2']['metadata'] == {'z': 1}
    assert 'metadata' not in tests_['unused_metadata']
    assert 'metadata' not in tests_['empty_metadata']
    assert tests_['unserializable_metadata']['metadata'].startswith('{\'a\':')


def test_environment_via_metadata_plugin(make_json):
    data = make_json('', ['--json-report', '--metadata', 'x', 'y'])
    assert 'Python' in data['environment']
    assert data['environment']['x'] == 'y'


def test_modifyreport_hook(testdir, make_json):
    testdir.makeconftest("""
        def pytest_json_modifyreport(json_report):
            json_report['foo'] = 'bar'
            del json_report['summary']
    """)
    data = make_json("""
        def test_foo():
            assert False
    """)
    assert data['foo'] == 'bar'
    assert 'summary' not in data


def test_warnings(make_json):
    warnings = make_json("""
        class TestFoo:
            def __init__(self):
                pass
            def test_foo(self):
                assert True
    """)['warnings']
    assert len(warnings) == 1
    assert set(warnings[0]) == {
        'filename', 'lineno', 'message', 'when'
    }
    assert warnings[0]['filename'].endswith('.py')
    assert warnings[0]['lineno'] == 1
    assert warnings[0]['when'] == 'collect'
    assert '__init__' in warnings[0]['message']


def test_process_report(testdir, make_json):
    testdir.makeconftest("""
        def pytest_sessionfinish(session):
            assert session.config._json_report.report['exitcode'] == 0
    """)
    testdir.makepyfile("""
        def test_foo():
            assert True
    """)
    res = testdir.runpytest('--json-report')
    assert res.ret == 0


def test_indent(testdir, make_json):
    testdir.runpytest('--json-report')
    with open(str(testdir.tmpdir / '.report.json')) as f:
        assert len(f.readlines()) == 1
    testdir.runpytest('--json-report', '--json-report-indent=4')
    with open(str(testdir.tmpdir / '.report.json')) as f:
        assert f.readlines()[1].startswith('    "')


def test_logging(make_json):
    data = make_json("""
        import logging
        import pytest

        @pytest.fixture
        def fixture(request):
            logging.info('log info')
            def f():
                logging.warn('log warn')
            request.addfinalizer(f)

        def test_foo(fixture):
            logging.error('log error')
            try:
                raise
            except RuntimeError:
                logging.getLogger().debug('log %s', 'debug', exc_info=True)
    """, ['--json-report', '--log-level=DEBUG'])
    test = data['tests'][0]
    assert test['setup']['log'][0]['msg'] == 'log info'
    assert test['call']['log'][0]['msg'] == 'log error'
    assert test['call']['log'][1]['msg'] == 'log debug'
    assert test['teardown']['log'][0]['msg'] == 'log warn'

    record = logging.makeLogRecord(test['call']['log'][1])
    assert record.getMessage() == record.msg == 'log debug'


def test_direct_invocation(testdir):
    test_file = testdir.makepyfile("""
        def test_foo():
            assert True
    """)
    plugin = JSONReport()
    res = pytest.main([test_file.strpath], plugins=[plugin])
    assert res == 0
    assert plugin.report['exitcode'] == 0

import json
import pytest


@pytest.fixture
def misc_testdir(testdir):
    # Some test cases borrowed from github.com/mattcl/pytest-json
    testdir.makepyfile("""
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
    """)
    return testdir


@pytest.fixture
def load_report(misc_testdir):
    def func(path='.report.json'):
        with open(str(misc_testdir.tmpdir / path)) as f:
            data = json.load(f)
        return data
    return func


@pytest.fixture
def json_data(misc_testdir, load_report):
    misc_testdir.runpytest('-vv', '--json-report')
    return load_report()


@pytest.fixture
def tests(json_data):
    return {test['domain'][5:]: test for test in json_data['tests']}


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
        json_report_file = ini2.json
    """)
    misc_testdir.runpytest('--json-report', '--json-report-file=arg2.json')
    assert (misc_testdir.tmpdir / 'arg2.json').exists()


def test_report_context(json_data):
    assert set(json_data) == set(['created', 'duration', 'python', 'pytest',
                                  'platform', 'tests', 'summary'])


def test_report_item_keys(tests):
    assert set(tests['pass']) == set(['nodeid', 'path', 'lineno', 'domain',
                                      'outcome', 'keywords', 'setup', 'call',
                                      'teardown'])


def test_report_outcomes(tests):
    assert len(tests) == 8
    assert tests['pass']['outcome'] == 'passed'
    assert tests['fail_with_fixture']['outcome'] == 'failed'
    assert tests['xfail']['outcome'] == 'xfailed'
    assert tests['xfail_but_passing']['outcome'] == 'xpassed'
    assert tests['fail_during_setup']['outcome'] == 'error'
    assert tests['fail_during_teardown']['outcome'] == 'error'
    assert tests['skip']['outcome'] == 'skipped'


def test_report_summary(json_data):
    assert json_data['summary'] == {
        'total': 8,
        'passed': 1,
        'failed': 2,
        'skipped': 1,
        'xpassed': 1,
        'xfailed': 1,
        'error': 2,
    }


def test_report_longrepr(json_data, tests):
    assert 'assert False' in tests['fail_with_fixture']['call']['longrepr']


def test_report_crash_and_traceback(tests):
    assert 'traceback' not in tests['pass']['call']
    call = tests['fail_nested']['call']
    assert call['crash'] == {
        'path': 'test_report_crash_and_traceback.py',
        'lineno': 54,
        'info': 'TypeError: unsupported operand type(s) for -: \'int\' and '
                '\'NoneType\''
    }
    assert call['traceback'] == [
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 65,
            'info': ''
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 63,
            'info': 'in foo'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 63,
            'info': 'in <listcomp>'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 59,
            'info': 'in bar'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 54,
            'info': 'TypeError'
        }
    ]


def test_no_traceback(misc_testdir, load_report):
    misc_testdir.runpytest('--json-report', '--json-report-no-traceback')
    tests_ = tests(load_report())
    assert 'traceback' not in tests_['fail_nested']['call']


def test_no_streams(misc_testdir, load_report):
    misc_testdir.runpytest('--json-report', '--json-report-no-streams')
    call = tests(load_report())['fail_with_fixture']['call']
    assert 'stdout' not in call
    assert 'stderr' not in call


def test_summary_only(misc_testdir, load_report):
    misc_testdir.runpytest('--json-report', '--json-report-summary')
    data = load_report()
    assert 'summary' in data
    assert 'tests' not in data


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

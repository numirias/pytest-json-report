import json
import pytest


@pytest.fixture
def misc_testdir(testdir):
    # Test cases borrowed from github.com/mattcl/pytest-json
    testdir.makepyfile("""
        import pytest


        @pytest.fixture
        def setup_teardown_fixture(request):
            print('setting up')
            def fn():
                print('tearing down')
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
    """)
    return testdir


@pytest.fixture
def json_data(misc_testdir):
    misc_testdir.runpytest('--json-report')
    with open(str(misc_testdir.tmpdir / '.report.json')) as f:
        data = json.load(f)
    return data


@pytest.fixture
def tests_by_name(json_data):
    return {test['domain'][5:]: test for test in json_data['tests']}


def test_arguments_in_help(misc_testdir):
    res = misc_testdir.runpytest('--help')
    res.stdout.fnmatch_lines(['*json-report*'])


def test_no_report(misc_testdir):
    misc_testdir.runpytest()
    assert not (misc_testdir.tmpdir / '.report.json').exists()


def test_create_report(misc_testdir):
    misc_testdir.runpytest('--json-report')
    assert (misc_testdir.tmpdir / '.report.json').exists()


def test_create_report_with_custom_file(misc_testdir):
    misc_testdir.runpytest('--json-report', '--json-report-file=foo.js')
    assert (misc_testdir.tmpdir / 'foo.js').exists()


def test_report_context(json_data):
    assert all(key in json_data for key in ['created', 'duration', 'python',
                                            'pytest', 'platform', 'tests'])


def test_report_tests(json_data, tests_by_name):
    tests = tests_by_name
    assert len(tests) == 7

    assert tests['pass']['outcome'] == 'passed'
    assert tests['fail_with_fixture']['outcome'] == 'failed'
    assert tests['xfail']['outcome'] == 'xfailed'
    assert tests['xfail_but_passing']['outcome'] == 'xpassed'
    assert tests['fail_during_setup']['outcome'] == 'error'
    assert tests['fail_during_teardown']['outcome'] == 'error'
    assert tests['skip']['outcome'] == 'skipped'

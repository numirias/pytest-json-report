import json
import pytest


@pytest.fixture
def misc_testdir(testdir):
    # Test fixture borrowed from github.com/mattcl/pytest-json
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
            assert 1 == 3
        @pytest.fixture
        def fail_teardown_fixture(request):
            def fn():
                assert 1 == 3
            request.addfinalizer(fn)
        def test_basic(json_report_path):
            print('call str')
            assert json_report_path == "herpaderp.json"
        def test_fail_with_fixture(setup_teardown_fixture):
            print('call str 2')
            assert 1 == 2
        @pytest.mark.xfail(reason='testing xfail')
        def test_xfailed():
            print('I am xfailed')
            assert 1 == 2
        @pytest.mark.xfail(reason='testing xfail')
        def test_xfailed_but_passing():
            print('I am xfailed but passing')
            assert 1 == 1
        def test_fail_during_setup(fail_setup_fixture):
            print('I failed during setup')
            assert 1 == 1
        def test_fail_during_teardown(fail_teardown_fixture):
            print('I will fail during teardown')
            assert 1 == 1
        @pytest.mark.skipif(True, reason='testing skip')
        def test_skipped():
            assert 1 == 2
    """)
    return testdir


@pytest.fixture
def json_data(misc_testdir):
    misc_testdir.runpytest('--json-report')
    with open(str(misc_testdir.tmpdir / '.report.json')) as f:
        data = json.load(f)
    return data


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


def test_report_tests(json_data):
    tests = json_data['tests']
    assert len(tests) == 7

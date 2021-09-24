import logging
import os.path
import sys
import pytest

from pytest_jsonreport.plugin import JSONReport
from .conftest import tests_only, FILE


def test_arguments_in_help(misc_testdir):
    res = misc_testdir.runpytest('--help')
    res.stdout.fnmatch_lines([
        '*json-report*',
        '*json-report-file*',
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


def test_create_no_report(misc_testdir):
    misc_testdir.runpytest('--json-report', '--json-report-file=NONE')
    assert not (misc_testdir.tmpdir / '.report.json').exists()


def test_terminal_summary(misc_testdir):
    res = misc_testdir.runpytest('--json-report')
    res.stdout.fnmatch_lines(['-*JSON report*-', '*report saved*.report.json*'])

    res = misc_testdir.runpytest('--json-report', '--json-report-file=./')
    res.stdout.fnmatch_lines(['*could not save report*'])

    res = misc_testdir.runpytest('--json-report', '--json-report-file=NONE')
    res.stdout.no_fnmatch_line('-*JSON report*-')

    res = misc_testdir.runpytest('--json-report', '--json-report-file=NONE', '-v')
    res.stdout.fnmatch_lines(['*auto-save skipped*'])

    res = misc_testdir.runpytest('--json-report', '-q')
    res.stdout.no_fnmatch_line('-*JSON report*-')

    res = misc_testdir.runpytest('--json-report', '-q', '--json-report-verbosity=0')
    res.stdout.fnmatch_lines(['-*JSON report*-'])

    res = misc_testdir.runpytest(
        '--json-report', '--json-report-file=NONE', '-vv', '--json-report-verbosity=0')
    res.stdout.no_fnmatch_line('-*JSON report*-')


def test_report_keys(num_processes, make_json):
    data = make_json()
    keys = set([
        'created', 'duration', 'environment', 'collectors', 'tests', 'summary',
        'root', 'exitcode'
    ])
    if num_processes > 0:
        # xdist only reports failing collectors
        keys.remove('collectors')
    assert set(data) == keys
    assert isinstance(data['created'], float)
    assert isinstance(data['duration'], float)
    assert os.path.isabs(data['root'])
    assert data['exitcode'] == 1


def test_report_collectors(num_processes, make_json):
    collectors = make_json().get('collectors', [])
    if num_processes > 0:
        # xdist only reports failing collectors
        assert len(collectors) == 0
        return
    assert len(collectors) == 2
    assert all(c['outcome'] == 'passed' for c in collectors)
    assert collectors[0] == {
        'nodeid': '',
        'outcome': 'passed',
        'result': [
            {
                'nodeid': 'test_report_collectors.py',
                'type': 'Module',
            }
        ]
    }
    assert {
        'nodeid': 'test_report_collectors.py::test_pass',
        'type': 'Function',
        'lineno': 25,
    } in collectors[1]['result']


def test_report_failed_collector(num_processes, make_json):
    data = make_json("""
        syntax error
        def test_foo():
            assert True
    """)

    collectors = data['collectors']
    assert data['tests'] == []
    if num_processes == 0:
        assert collectors[0]['outcome'] == 'passed'
        assert collectors[1]['outcome'] == 'failed'
        assert collectors[1]['result'] == []
        assert 'longrepr' in collectors[1]
    else:
        # xdist only reports failing collectors
        assert collectors[0]['outcome'] == 'failed'
        assert collectors[0]['result'] == []
        assert 'longrepr' in collectors[0]


def test_report_failed_collector2(num_processes, make_json):
    data = make_json("""
        import nonexistent
        def test_foo():
            pass
    """)
    collectors = data['collectors']
    # xdist only reports failing collectors
    idx = 1 if num_processes == 0 else 0
    assert collectors[idx]['longrepr'].startswith('ImportError')


def test_report_item_keys(tests):
    assert set(tests['pass']) == set([
        'nodeid', 'lineno', 'outcome', 'keywords', 'setup', 'call',
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
        'collected': 10,
    }


def test_report_longrepr(tests):
    assert 'assert False' in tests['fail_with_fixture']['call']['longrepr']


def test_report_crash_and_traceback(tests):
    assert 'traceback' not in tests['pass']['call']
    call = tests['fail_nested']['call']
    assert call['crash']['path'].endswith('test_report_crash_and_traceback.py')
    assert call['crash']['lineno'] == 55
    assert call['crash']['message'].startswith('TypeError: unsupported ')
    traceback = [
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 66,
            'message': ''
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 64,
            'message': 'in foo'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 64,
            'message': 'in <listcomp>'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 60,
            'message': 'in bar'
        },
        {
            'path': 'test_report_crash_and_traceback.py',
            'lineno': 55,
            'message': 'TypeError'
        }
    ]
    if sys.version_info < (3,):
        del traceback[2]
    assert call['traceback'] == traceback


def test_report_traceback_styles(make_json):
    """Handle different traceback styles (`--tb=...`)."""
    code = '''
        def test_raise(): assert False
        def test_raise_nested(): f = lambda: g; f()
    '''
    for style in ('long', 'short'):
        data = make_json(code, ['--json-report', '--tb=%s' % style])
        for i in (0, 1):
            assert isinstance(data['tests'][i]['call']['traceback'], list)

    for style in ('native', 'line', 'no'):
        data = make_json(code, ['--json-report', '--tb=%s' % style])
        for i in (0, 1):
            assert 'traceback' not in data['tests'][i]['call']


def test_report_item_deselected(make_json):
    data = make_json("""
        import pytest
        @pytest.mark.good
        def test_first():
            pass
        @pytest.mark.bad
        def test_second():
            pass
    """, ['--json-report', '-m', 'not bad'])
    assert data['summary']['collected'] == 1
    assert not data['collectors'][1]['result'][0].get('deselected')
    assert data['collectors'][1]['result'][1].get('deselected')


def test_no_traceback(make_json):
    data = make_json(FILE, ['--json-report', '--json-report-omit=traceback'])
    tests_ = tests_only(data)
    assert 'traceback' not in tests_['fail_nested']['call']


def test_pytest_no_traceback(make_json):
    data = make_json(FILE, ['--json-report', '--tb=no'])
    tests_ = tests_only(data)
    assert 'traceback' not in tests_['fail_nested']['call']


def test_no_streams(make_json):
    data = make_json(FILE, ['--json-report', '--json-report-omit=streams'])
    call = tests_only(data)['fail_with_fixture']['call']
    assert 'stdout' not in call
    assert 'stderr' not in call


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


def test_record_property(make_json, num_processes):
    data = make_json("""
        def test_record_property(record_property):
            record_property('foo', 42)
            record_property('bar', ['baz', {'x': 'y'}])
            record_property('foo', 43)
            record_property(123, 456)

        def test_record_property_empty(record_property):
            assert True

        def test_record_property_unserializable(record_property):
            record_property('foo', b'somebytes')
    """)
    tests_ = tests_only(data)
    assert tests_['record_property']['user_properties'] == \
        [{'foo': 42}, {'bar': ['baz', {'x': 'y'}]}, {'foo': 43}, {'123': 456}]
    assert 'user_properties' not in tests_['record_property_empty'].keys()
    # TODO Relay warnings correctly when using xdist
    if num_processes == 0:
        assert len(data['warnings']) == 1 and (
            'not JSON-serializable' in data['warnings'][0]['message'])


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

        import pytest
        @pytest.fixture
        def stage(json_metadata):
            json_metadata['a'] = 1
            yield
            json_metadata['c'] = 3

        def test_multi_stage_metadata(json_metadata, stage):
            json_metadata['b'] = 2
    """)
    tests_ = tests_only(data)
    assert tests_['metadata1']['metadata'] == {'x': 'foo', 'y': [1, {'a': 2}]}
    assert tests_['metadata2']['metadata'] == {'z': 1}
    assert 'metadata' not in tests_['unused_metadata']
    assert 'metadata' not in tests_['empty_metadata']
    assert 'metadata' not in tests_['unserializable_metadata']
    assert len(data['warnings']) == 1 and (
        'test_unserializable_metadata is not JSON-serializable' in
        data['warnings'][0]['message'])
    assert \
        tests_['multi_stage_metadata']['metadata'] == {'a': 1, 'b': 2, 'c': 3}


def test_metadata_fixture_without_report_flag(testdir):
    """Using the json_metadata fixture without --json-report should not raise
    internal errors."""
    testdir.makepyfile('''
        def test_metadata(json_metadata):
            json_metadata['x'] = 'foo'
    ''')
    res = testdir.runpytest()
    assert res.ret == 0
    assert not (testdir.tmpdir / '.report.json').exists()


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


def test_runtest_stage_hook(testdir, make_json):
    testdir.makeconftest("""
        def pytest_json_runtest_stage(report):
            return {'outcome': report.outcome}
    """)
    data = make_json("""
        def test_foo():
            assert False
    """)
    test = data['tests'][0]
    assert test['setup'] == {'outcome': 'passed'}
    assert test['call'] == {'outcome': 'failed'}
    assert test['teardown'] == {'outcome': 'passed'}


def test_runtest_metadata_hook(testdir, make_json):
    testdir.makeconftest("""
        def pytest_json_runtest_metadata(item, call):
            if call.when != 'call':
                return {}
            return {'id': item.nodeid, 'start': call.start, 'stop': call.stop}
    """)
    data = make_json("""
        def test_foo():
            assert False
    """)
    test = data['tests'][0]
    assert test['metadata']['id'].endswith('::test_foo')
    assert isinstance(test['metadata']['start'], float)
    assert isinstance(test['metadata']['stop'], float)


def test_warnings(make_json, num_processes):
    warnings = make_json("""
        class TestFoo:
            def __init__(self):
                pass
            def test_foo(self):
                assert True
    """)['warnings']
    assert len(warnings) == max(1, num_processes)
    assert set(warnings[0]) == {
        'category', 'filename', 'lineno', 'message', 'when'
    }
    assert warnings[0]['category'] in (
        'PytestCollectionWarning',
        'PytestWarning'
    )
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
            except (RuntimeError, TypeError): # TypeError is raised in Py 2.7
                logging.getLogger().debug('log %s', 'debug', exc_info=True)
    """, ['--json-report', '--log-level=DEBUG'])

    test = data['tests'][0]
    assert test['setup']['log'][0]['msg'] == 'log info'
    assert test['call']['log'][0]['msg'] == 'log error'
    assert test['call']['log'][1]['msg'] == 'log debug'
    assert test['teardown']['log'][0]['msg'] == 'log warn'

    record = logging.makeLogRecord(test['call']['log'][1])
    assert record.getMessage() == record.msg == 'log debug'


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
    """, ['--json-report', '--json-report-omit=log'])
    assert 'log' not in data['tests'][0]['call']


def test_no_keywords(make_json):
    data = make_json()
    assert 'keywords' in data['tests'][0]

    data = make_json(args=['--json-report', '--json-report-omit=keywords'])
    assert 'keywords' not in data['tests'][0]


def test_no_collectors(make_json, num_processes):
    data = make_json()
    if num_processes == 0:
        # xdist only reports failing collectors
        assert 'collectors' in data

    data = make_json(args=['--json-report', '--json-report-omit=collectors'])
    assert 'collectors' not in data


def test_no_warnings(make_json, num_processes):
    assert 'warnings' not in make_json("""
        class TestFoo:
            def __init__(self):
                pass
            def test_foo(self):
                assert True
    """, args=['--json-report', '--json-report-omit=warnings'])


def test_direct_invocation(testdir):
    test_file = testdir.makepyfile("""
        def test_foo():
            assert True
    """)
    plugin = JSONReport()
    res = pytest.main([test_file.strpath], plugins=[plugin])
    assert res == 0
    assert plugin.report['exitcode'] == 0
    assert plugin.report['summary']['total'] == 1

    report_path = testdir.tmpdir / 'foo_report.json'
    assert not report_path.exists()
    plugin.save_report(str(report_path))
    assert report_path.exists()


def test_xdist(make_json, match_reports):
    r1 = make_json(FILE, ['--json-report'])
    r2 = make_json(FILE, ['--json-report', '-n=1'])
    r3 = make_json(FILE, ['--json-report', '-n=4'])
    assert match_reports(r1, r2)
    assert match_reports(r2, r3)


def test_bug_31(make_json):
    data = make_json('''
        from flaky import flaky

        FLAKY_RUNS = 0

        @flaky
        def test_flaky_pass():
            assert 1 + 1 == 2

        @flaky
        def test_flaky_fail():
            global FLAKY_RUNS
            FLAKY_RUNS += 1
            assert FLAKY_RUNS == 2
    ''')
    assert set(data['summary'].items()) == {
        ('total', 2),
        ('passed', 2),
        ('collected', 2),
    }


def test_bug_37(testdir):
    """#37: Report is not accessible via config._json_report when pytest is run
    from code via pytest.main().
    """
    test_file = testdir.makepyfile("""
        def test_foo():
            assert True
    """)
    testdir.makeconftest("""
        def pytest_sessionfinish(session):
            assert session.config._json_report.report['exitcode'] == 0
    """)
    plugin = JSONReport()
    pytest.main([test_file.strpath], plugins=[plugin])


def test_bug_41(misc_testdir):
    """#41: Create report file path if it doesn't exist."""
    misc_testdir.runpytest('--json-report', '--json-report-file=x/report.json')
    assert (misc_testdir.tmpdir / 'x/report.json').exists()


def test_bug_69(testdir):
    """#69: Handle deselection of test items that have not been collected."""
    fn = testdir.makepyfile('''
        def test_pass():
            assert True
        def test_fail():
            assert False
    ''').strpath
    assert testdir.runpytest('--json-report', fn).ret == 1
    # In this second run, `--last-failed` causes `test_pass` to not be
    # *collected* but still explicitly *deselected*, so we assert there is no
    # internal error caused by trying to access the collector obj.
    assert testdir.runpytest('--json-report', '--last-failed', fn).ret == 1

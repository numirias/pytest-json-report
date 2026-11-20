import json

import pytest


@pytest.mark.parametrize('content,reruns,outcome,exitcode,stages', [
    ('''
        def test_flaky(request):
            assert request.node.execution_count > 1
    ''', 1, 'passed', 0, ('setup', 'call', 'teardown')),
    ('''
        def test_flaky(request):
            assert request.node.execution_count > 2
    ''', 2, 'passed', 0, ('setup', 'call', 'teardown')),
    ('''
        import pytest

        @pytest.fixture
        def fixture(request):
            assert request.node.execution_count > 1

        def test_flaky(fixture):
            pass
    ''', 1, 'passed', 0, ('setup', 'call', 'teardown')),
    ('''
        def test_flaky():
            assert False
    ''', 1, 'failed', 1, ('setup', 'call', 'teardown')),
    ('''
        import pytest

        @pytest.fixture
        def fixture(request):
            if request.node.execution_count > 1:
                pytest.fail('setup failed on the retry')

        def test_flaky(fixture):
            assert False
    ''', 1, 'error', 1, ('setup', 'teardown')),
    ('''
        import pytest

        def test_flaky(request):
            if request.node.execution_count > 1:
                pytest.skip('skip on the retry')
            assert False
    ''', 1, 'skipped', 0, ('setup', 'call', 'teardown')),
])
def test_rerun_reports_final_attempt(
        testdir, num_processes, content, reruns, outcome, exitcode, stages):
    testdir.makepyfile(content)
    testdir.runpytest_subprocess(
        '--json-report', '--reruns=%d' % reruns, '-n=%d' % num_processes,
    )
    with open(str(testdir.tmpdir / '.report.json')) as stream:
        report = json.load(stream)

    assert report['exitcode'] == exitcode
    assert report['summary'] == {outcome: 1, 'collected': 1, 'total': 1}
    assert len(report['tests']) == 1
    test = report['tests'][0]
    assert test['outcome'] == outcome
    assert set(test).intersection(('setup', 'call', 'teardown')) == set(stages)

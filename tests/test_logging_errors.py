import logging

import pytest

from pytest_jsonreport.plugin import LoggingHandler


class BrokenMessage:
    def __str__(self):
        raise ValueError('broken log message')


@pytest.mark.parametrize('raise_errors', [False, True])
@pytest.mark.parametrize('message,args', [
    (BrokenMessage(), ()),
    ('number %d', ('not a number',)),
    ('two %s %s', ('one',)),
])
def test_logging_format_error_uses_error_policy(
        monkeypatch, capsys, raise_errors, message, args):
    monkeypatch.setattr(logging, 'raiseExceptions', raise_errors)
    handler = LoggingHandler()
    record = logging.LogRecord('example', logging.ERROR, __file__, 1,
                               message, args, None)

    handler.handle(record)

    assert handler.records == []
    assert bool(capsys.readouterr().err) == raise_errors
    valid = logging.LogRecord('example', logging.ERROR, __file__, 2,
                              'valid %s', ('message',), None)
    handler.handle(valid)
    assert [entry['msg'] for entry in handler.records] == ['valid message']
    assert handler.records[0]['args'] is None


@pytest.mark.parametrize('error', [KeyboardInterrupt, SystemExit, RecursionError])
def test_logging_critical_errors_propagate(monkeypatch, error):
    class CriticalMessage:
        def __str__(self):
            raise error()

    monkeypatch.setattr(logging, 'raiseExceptions', False)
    handler = LoggingHandler()
    record = logging.LogRecord('example', logging.ERROR, __file__, 1,
                               CriticalMessage(), (), None)
    with pytest.raises(error):
        handler.handle(record)
    assert handler.records == []


def test_logging_error_does_not_fail_passing_test(make_json):
    report = make_json('''
        import logging

        class BrokenMessage:
            def __str__(self):
                raise ValueError('broken log message')

        def test_log_error(monkeypatch):
            monkeypatch.setattr(logging, 'raiseExceptions', False)
            logging.error(BrokenMessage())
            logging.error('valid %s', 'message')
    ''')
    assert report['exitcode'] == 0
    assert report['summary']['passed'] == 1
    assert report['tests'][0]['outcome'] == 'passed'
    assert [entry['msg'] for entry in report['tests'][0]['call']['log']] == [
        'valid message']

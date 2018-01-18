import json


class PytestJSONReport:

    def __init__(self, report_file):
        self.report_file = report_file

    def pytest_terminal_summary(self, terminalreporter, exitstatus):
        items = []
        for key, reports in terminalreporter.stats.items():
            if key not in ['passed', 'failed']:
                continue
            for report in reports:
                location = getattr(report, 'location', (None, None, None))
                item = {
                    'path': location[0],
                    'line': location[1],
                    'domain': location[2],
                    'outcome': getattr(report, 'outcome', None),
                    'when': getattr(report, 'when', None),
                    'nodeid': getattr(report, 'nodeid', None),
                    'duration': getattr(report, 'duration', None),
                    'keywords': getattr(report, 'keywords', {}),
                    'longrepr': str(getattr(report, 'longrepr', '')),
                }
                items.append(item)
        with open(self.report_file, 'w') as f:
            json.dump(items, f)


def pytest_addoption(parser):
    group = parser.getgroup('jsonreport', 'reporting test results as JSON')
    group.addoption('--json-report', default=False, action='store_true',
                    help='create JSON report')
    group.addoption('--json-report-file', default='.report.json',
                    help='target file to save JSON report')


def pytest_configure(config):
    if config.option.json_report:
        plugin = PytestJSONReport(config.option.json_report_file)
        config.pluginmanager.register(plugin)

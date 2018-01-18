from setuptools import setup


setup(
    name='pytest-json-report',
    description='A pytest plugin to report test results to JSON files',
    packages=['pytest_jsonreport'],
    author='numirias',
    author_email='numirias@users.noreply.github.com',
    version='0.1',
    url='https://github.com/numirias/pytest-json-report',
    license='MIT',
    entry_points={
        'pytest11': [
            'pytest_jsonreport = pytest_jsonreport.plugin',
        ]
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Pytest',
    ],
)

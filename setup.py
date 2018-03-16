from setuptools import setup


setup(
    name='pytest-json-report',
    description='A pytest plugin to report test results as JSON files',
    packages=['pytest_jsonreport'],
    author='numirias',
    author_email='numirias@users.noreply.github.com',
    version='0.7.0',
    url='https://github.com/numirias/pytest-json-report',
    license='MIT',
    install_requires=[
        'pytest>=3.3.2',
        'pytest-metadata',
    ],
    entry_points={
        'pytest11': [
            'pytest_jsonreport = pytest_jsonreport.plugin',
        ]
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: Pytest',
    ],
)

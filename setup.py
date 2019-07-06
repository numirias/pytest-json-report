from os import path
import sys

from setuptools import setup

# Open encoding isn't available for Python 2.7 (sigh)
if sys.version_info < (3, 0):
    from io import open


this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name='pytest-json-report',
    description='A pytest plugin to report test results as JSON files',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=['pytest_jsonreport'],
    author='numirias',
    author_email='numirias@users.noreply.github.com',
    version='1.1.0',
    url='https://github.com/numirias/pytest-json-report',
    license='MIT',
    install_requires=[
        'pytest>=4.2.0',
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
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Framework :: Pytest',
    ],
)

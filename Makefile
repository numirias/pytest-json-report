SOURCE_DIR=pytest_jsonreport/

init:
	pip install pipenv --upgrade
	pipenv install --dev --skip-lock
test:
	tox
lint:
	pipenv run flake8
	pipenv run pylint --rcfile setup.cfg ${SOURCE_DIR}
publish:
	rm -rf *.egg-info build/ dist/
	python setup.py bdist_wheel sdist
	twine upload -r pypi dist/*
	rm -rf *.egg-info build/ dist/

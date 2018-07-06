install:
	pip3 install .

test:
	cd tests && python -m unittest test_completer.py

style-check:
	pycodestyle itask tests --show-source --statistics

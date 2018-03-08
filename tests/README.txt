Unit tests
==========

1/ Environnement:
export PLACEMENT_ROOT=$(cd ..;pwd)
export PYTHONPATH=$PLACEMENT_ROOT/lib:$PYTHONPATH

2/ Execute the tests:
python TestUtilities.py
python TestHardware.py
python TestArchitecture.py
python TestScatter.py
python TestCompact.py

3/ If all tests are OK, you can measure the coverage:
python-coverage run    TestUtilities.py
python-coverage run -a TestHardware.py
python-coverage run -a TestArchitecture.py
python-coverage run -a TestScatter.py
python-coverage run -a TestCompact.py
python-coverage report -m

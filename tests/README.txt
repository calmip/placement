Unit tests
==========

1/ Environnement:
export PLACEMENT_ROOT=$(cd ..;pwd)
export PYTHONPATH=$PLACEMENT_ROOT/lib:$PYTHONPATH

2/ Execute the tests:
python3 TestUtilities.py
python3 TestHardware.py
python3 TestArchitecture.py
python3 TestScatter.py
python3 TestCompact.py

3/ If all tests are OK, you can measure the coverage:
python-coverage run    TestUtilities.py
python-coverage run -a TestHardware.py
python-coverage run -a TestArchitecture.py
python-coverage run -a TestScatter.py
python-coverage run -a TestCompact.py
python-coverage report -m

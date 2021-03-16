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
python3-coverage run    TestUtilities.py
python3-coverage run -a TestHardware.py
python3-coverage run -a TestArchitecture.py
python3-coverage run -a TestScatter.py
python3-coverage run -a TestCompact.py
python3-coverage report -m

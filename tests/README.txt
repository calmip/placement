Test unitaires
==============

1/ Environnement:
export PYTHONPATH=$(pwd)/usr/local/lib/placement

2/ Exécuter les tests:
python tests/TestUtilities.py
python tests/TestArchitecture.py
python tests/TestRunning.py
python tests/TestScatter.py
python tests/TestCompact.py

3/ Mesurer la couverture (si les tests sont corects):
python-coverage run    tests/TestUtilities.py
python-coverage run -a tests/TestScatter.py
python-coverage run -a tests/TestCompact.py
python-coverage report -m



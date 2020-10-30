
from utilities import AnsiCodes

for i in range(0,32):
	print (AnsiCodes.map(i) + "toto" + AnsiCodes.normal())


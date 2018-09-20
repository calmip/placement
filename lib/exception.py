#! /usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2015-2018 Emmanuel Courcelle
#  PLACEMENT is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

import sys

class PlacementException(Exception):
    def __init__(self,msg,err=None):
        Exception.__init__(self,msg)
        self.err=err
    
def ManageException(e):
    print("PLACEMENT_ERROR_FOUND")
    print("PLACEMENT " + str(e), file = sys.stderr)

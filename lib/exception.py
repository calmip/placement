#! /usr/bin/env python
# -*- coding: utf-8 -*-

#  Copyright (C) 2015-2018 Emmanuel Courcelle
#  PLACEMENT is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.

class PlacementException(Exception):
    def __init__(self,msg):
        Exception.__init__(self,msg)
    pass


# Copyright (C) 2016 Davit Samvelyan
#
# This file is part of ycmd.
#
# ycmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ycmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa


# Filename token.py conflicts with the python internals.

class Token( object ):
  """Represents single semantic token.
  kind attribute groups tokens of certain types into higher level abstractions.
       Possible values are: (Punctuation, Comment, Keyword, Literal, Identifier).
  type represents token type (Keyword, Class, Enumeration, ...),
  range is the token's source range.

  Possible combinations of (kind, type) are:

    ( Punctuation, Punctuation ),

    ( Comment, Comment ),

    ( Keyword, Keyword ),

    ( Literal, Integer ),
    ( Literal, Floating ),
    ( Literal, Imaginary ),
    ( Literal, String ),
    ( Literal, Character ),

    ( Identifier, Namespace ),
    ( Identifier, Class ),
    ( Identifier, Struct ),
    ( Identifier, Union ),
    ( Identifier, TypeAlias ),
    ( Identifier, MemberVariable ),
    ( Identifier, Variable ),
    ( Identifier, Function ),
    ( Identifier, FunctionParameter ),
    ( Identifier, Enumeration ),
    ( Identifier, Enumerator ),
    ( Identifier, TemplateParameter ),
    ( Identifier, TemplateNonTypeParameter ),
    ( Identifier, PreprocessingDirective ),
    ( Identifier, Macro ),
    ( Identifier, Unsupported )"""

  def __init__ ( self, kind, token_type, token_range ):
    self.kind = kind
    self.type = token_type
    self.range = token_range


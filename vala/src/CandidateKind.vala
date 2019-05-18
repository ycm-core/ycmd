// Copyright (C) 2019 Jakub Kaszycki
//
// This file is part of ycmd.
//
// ycmd is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// ycmd is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with ycmd.  If not, see <http://www.gnu.org/licenses/>.

public enum Ycmvala.CandidateKind {
  STRUCT,
  CLASS,
  ENUM,
  ERROR,
  TYPE,
  FIELD,
  METHOD,
  VARIABLE,
  PARAMETER,
  PROPERTY,
  NAMESPACE,
  SIGNAL,
  UNKNOWN;

  internal static CandidateKind from_symbol( Vala.Symbol symbol ) {
    if ( symbol is Vala.Struct ) {
      return ((Vala.Struct) symbol).is_simple_type() ? TYPE : STRUCT;
    } else if ( symbol is Vala.Class )
      return CLASS;
    else if ( symbol is Vala.Enum )
      return ENUM;
    else if ( symbol is Vala.ErrorCode || symbol is Vala.ErrorDomain )
      return ERROR;
    else if ( symbol is Vala.Field )
      return FIELD;
    else if ( symbol is Vala.Method )
      return METHOD;
    else if ( symbol is Vala.Parameter
              || symbol is Vala.TypeParameter )
      return PARAMETER;
    else if ( symbol is Vala.Variable )
      return VARIABLE;
    else if ( symbol is Vala.Property )
      return PROPERTY;
    else if ( symbol is Vala.Namespace )
      return NAMESPACE;
    else if ( symbol is Vala.Signal )
      return SIGNAL;
    else
      return UNKNOWN;
  }

  public static unowned string to_string( CandidateKind kind ) {
    var clazz = (EnumClass) typeof( CandidateKind ).class_ref();
    unowned EnumValue? val = clazz.get_value( kind );
    return_val_if_fail( val != null, null );
    return ((!) val).value_nick;
  }
}

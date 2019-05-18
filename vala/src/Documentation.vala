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

public class Ycmvala.Documentation : Object {
  public string brief_description { get; construct; }
  public string display_name { get; construct; }
  public string long_description { get; construct; }
  public string text { get; construct; }
  public string type_name { get; construct; }

  public Documentation( string text,
                        string brief_description,
                        string type_name,
                        string display_name,
                        string long_description ) {
    Object( brief_description: brief_description,
            display_name: display_name,
            long_description: long_description,
            text: text,
            type_name: type_name );
  }

  internal Documentation.vala( Vala.Symbol symbol ) {
    string long_description;

    if ( symbol.comment != null ) {
      var comment = (!) symbol.comment;

      long_description = convert_comment( comment.content );
    } else {
      long_description = "(No documentation available)";
    }

    Object( brief_description: generate_brief_description( long_description ),
            display_name: (!) symbol.name,
            long_description: long_description,
            text: symbol.get_full_name(),
            type_name: symbol_type_name( symbol ) );
  }

  private static string generate_brief_description( string long_description ) {
    var sb = new StringBuilder( long_description.substring(
      0, int.min( long_description.index_of( "\n\n" ),
                  long_description.index_of_char( '.' ) )
    ) );

    if ( sb.len == 0 )
      return (owned) sb.str;

    if ( sb.str[ sb.len - 1] != '.' )
      sb.append_c( '.' );

    return (owned) sb.str;
  }

  private static string convert_comment( string comment_text ) {
    // I could use a regex, but this automaton is just prettier

    bool after_newline = true;
    uint len = comment_text.length;
    var sb = new StringBuilder.sized( len );

    for ( uint i = 0; i < len; i ++ ) {
      var ch = comment_text[ i ];

      if ( after_newline )
        switch ( ch ) {
          case ' ':
          case '\t':
          case '*':
            continue;
        }

      sb.append_c( ch );
      after_newline = ch == '\n';
    }

    return (owned) sb.str;
  }

  private static unowned string symbol_type_name( Vala.Symbol symbol ) {
    if ( symbol is Vala.Class )
      return ((Vala.Class) symbol).is_abstract ? "abstract class" : "class";
    else if ( symbol is Vala.EnumValue )
      return "enumerator";
    else if ( symbol is Vala.Constant )
      return "constant";
    else if ( symbol is Vala.Constructor )
      return "constructor";
    else if ( symbol is Vala.CreationMethod )
      return "creation method";
    else if ( symbol is Vala.Delegate )
      return "delegate";
    else if ( symbol is Vala.Destructor )
      return "destructor";
    else if ( symbol is Vala.DynamicMethod )
      return "dynamic method";
    else if ( symbol is Vala.DynamicProperty )
      return "dynamic property";
    else if ( symbol is Vala.DynamicSignal )
      return "dynamic signal";
    else if ( symbol is Vala.Enum )
      return "enumeration";
    else if ( symbol is Vala.ErrorCode )
      return "error code";
    else if ( symbol is Vala.ErrorDomain )
      return "error domain";
    else if ( symbol is Vala.Field )
      return "field";
    else if ( symbol is Vala.Interface )
      return "interface";
    else if ( symbol is Vala.LocalVariable )
      return "local variable";
    else if ( symbol is Vala.Method )
      return "method";
    else if ( symbol is Vala.Namespace )
      return "namespace";
    else if ( symbol is Vala.ObjectTypeSymbol )
      return "unknown object type";
    else if ( symbol is Vala.Parameter )
      return "parameter";
    else if ( symbol is Vala.Property )
      return "property";
    else if ( symbol is Vala.PropertyAccessor )
      return "property accessor";
    else if ( symbol is Vala.Signal )
      return "signal";
    else if ( symbol is Vala.Struct ) {
      var st = ((Vala.Struct) symbol);

      if ( st.is_boolean_type() )
        return "boolean type";
      else if ( st.is_decimal_floating_type() )
        return "decimal floating point type";
      else if ( st.is_floating_type() )
        return "floating point type";
      else if ( st.is_integer_type() )
        return "integer type";
      else if ( st.is_simple_type() )
        return "simple structure";
      else
        return "structure";
    } else if ( symbol is Vala.Subroutine )
      return "unknown subroutine";
    else if ( symbol is Vala.TypeParameter )
      return "type parameter";
    else if ( symbol is Vala.TypeSymbol )
      return "unknown type";
    else if ( symbol is Vala.UnresolvedSymbol )
      return "unresolved symbol";
    else if ( symbol is Vala.Variable )
      return "variable";
    else
      return "unknown symbol";
  }
}

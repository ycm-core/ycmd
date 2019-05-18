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

public class Ycmvala.Candidate : Object {
  public CandidateKind candidate_kind { get; construct; }
  public string detailed_information { get; construct; }
  public Documentation? documentation { get; construct; }
  public string? extra_menu_information { get; construct; }
  public string insertion_text { get; construct; }
  public string menu_text { get; construct; }

  public Candidate( string insertion_text,
                    string menu_text,
                    string extra_menu_information,
                    CandidateKind candidate_kind,
                    string detailed_information,
                    Documentation? documentation = null ) {
    Object( candidate_kind: candidate_kind,
            detailed_information: detailed_information,
            documentation: documentation,
            extra_menu_information: extra_menu_information,
            insertion_text: insertion_text,
            menu_text: menu_text );
  }

  internal Candidate.vala_symbol( Vala.Symbol symbol,
                                  string? name = null) {
    var doc = new Documentation.vala( symbol );

    Object( candidate_kind: CandidateKind.from_symbol( symbol ),
            detailed_information: "",
            documentation: doc,
            extra_menu_information: generate_extra_menu_information( symbol ),
            insertion_text: name != null ? (!) name : generate_insertion_text( symbol ),
            menu_text: generate_menu_text( symbol ) );
  }

  private static string? generate_extra_menu_information( Vala.Symbol symbol ) {
    if ( symbol is Vala.Constructor || symbol is Vala.CreationMethod )
      return null;
    else if ( symbol is Vala.Callable )
      return type_to_string( ((Vala.Callable) symbol).return_type );
    else if ( symbol is Vala.Property )
      return type_to_string( (!) ((Vala.Property) symbol).property_type );
    else if ( symbol is Vala.Variable )
      return type_to_string( (!) ((Vala.Variable) symbol).variable_type );
    else
      return null;
  }

  private static string generate_insertion_text( Vala.Symbol symbol ) {
    if ( symbol is Vala.Constructor ) {
      return "this." + (!) symbol.name;
    }

    return (!) symbol.name;
  }

  private static string generate_menu_text( Vala.Symbol symbol ) {
    if ( symbol is Vala.Callable ) {
      var callable = (Vala.Callable) symbol;

      var sb = new StringBuilder( (!) symbol.name );
      sb.append_c( '(' );

      bool first = true;

      foreach ( var param in callable.get_parameters() ) {
        if ( param.name == "this" )
          continue;
        if ( !first )
          sb.append( ", ");

        sb.append( parameter_to_string( param ) );
        first = false;
      }

      sb.append_c( ')' );

      return (owned) sb.str;
    }

    return (!) symbol.name;
  }

  private static string parameter_to_string( Vala.Parameter param ) {
    if ( param.ellipsis )
      return "...";

    return "%s %s".printf( ((!) param.variable_type).to_string(), (!) param.name );
  }

  private static string type_to_string( Vala.DataType type ) {
    if ( type is Vala.VoidType )
      return "void";
    else
      return (!) type.data_type.name;
  }
}

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

public class Ycmvala.TranslationUnit : Object
{
  public string filename { get; construct; }
  public Flags flags { get; construct; }

  private Vala.CodeContext? code_context = null;
  private GenericArray< Diagnostic > diagnostics = new GenericArray< Diagnostic >();
  private HashTable< string, HashTable< uint, BinarySearchDiagnosticArray > > diagnostics_for_location
    = new HashTable< string, HashTable< uint, BinarySearchDiagnosticArray > >( str_hash, str_equal );

  // Cache the node tree in case a build fails for imprecise stuff to work
  private Vala.SourceFile? main_file = null;
  private Vala.Namespace root_ns;
  private HashTable< Vala.Scope, CandidateTrie > candidates
    = new HashTable< Vala.Scope, CandidateTrie > ( direct_hash, direct_equal );

  internal TranslationUnit( string filename,
                            Flags flags,
                            HashTable< string, Bytes > unsaved_files ) throws CompleterError {
    Object( filename: filename,
            flags: flags );

    reparse( unsaved_files );
  }

  private void build_candidates( Vala.Scope scope ) {
    if ( scope.parent_scope != (Vala.Scope) null
         && !candidates.contains( scope.parent_scope ) )
      build_candidates( scope.parent_scope );

    var trie = new CandidateTrie();
    Utils.for_each_symbol( scope, ( key, symbol ) => {
      trie.@set( key, new Candidate.vala_symbol( symbol, key ), true );
      return true;
    }, false );

    if ( scope.parent_scope != (Vala.Scope) null )
      trie.set_all( candidates[ scope.parent_scope ], false );

    candidates[ scope ] = (owned) trie;
  }

  private bool can_fix( string message ) {
    // TODO
    return false;
  }

  public Candidate[] complete( int line,
                               int column,
                               HashTable< string, Bytes > unsaved_files,
                               bool reparse = true ) throws CompleterError {
    return complete_with_prefix( line, column, "", unsaved_files, reparse );
  }

  public Candidate[] complete_with_prefix( int line,
                                           int column,
                                           string prefix,
                                           HashTable< string, Bytes > unsaved_files,
                                           bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var candids = new GenericArray< Candidate >();

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      Vala.Symbol sym;
      if ( node is Vala.MemberAccess
           && ((Vala.MemberAccess) node).inner != null )
        sym = Utils.expression_type( (!) ((Vala.MemberAccess) node).inner ).data_type;
      else {
        var sym_nullable = Utils.find_parent_symbol( node );

        if ( sym_nullable == null )
          throw new CompleterError.INVALID_NODE(
            "Node without symbol parent: %s", node.to_string()
          );

        sym = (!) sym_nullable;
      }

      if ( !candidates.contains( sym.scope ) )
        build_candidates( sym.scope );

      candidates[ sym.scope ].build( prefix, candids );

      candids.sort( ( c1, c2 ) => strcmp( c1.menu_text, c2.menu_text ) );

      return (owned) candids.data;
    }
  }

  public string debug_get_node( int line,
                                int column,
                                HashTable< string, Bytes > unsaved_files,
                                bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      var sb = new StringBuilder( Type.from_instance( node ).name() );
      sb.append_printf( "@%p\n", node );

      sb.append( "to_string(): " ).append( node.to_string() ).append_c( '\n' );
      sb.append( "Parent node: " );
      if ( node.parent_node != null )
        sb.append( ((!) node.parent_node).to_string() );
      else
        sb.append( "<none>" );
      sb.append_c( '\n' );

      if ( node is Vala.Symbol ) {
        var sym = (Vala.Symbol) node;

        sb.append( "Parent symbol: " );

        if ( sym.parent_symbol != null )
          sb.append( ((!) sym.parent_symbol).to_string() );
        else
          sb.append( "<none>" );
        sb.append_c( '\n' );

        sb.append( "Name: " ).append( sym.name ?? "<none>" ).append_c( '\n' );
      }

      return (owned) sb.str;
    }
  }

  private void diagnostic_add( DiagnosticKind kind,
                               Range range,
                               string message,
                               bool can_fix ) {
    var diagnostic = new Diagnostic( kind, range, message, can_fix );
    diagnostics.add( diagnostic );

    HashTable< uint, BinarySearchDiagnosticArray > inner_table;

    var file = (!) (range.begin.file ?? "<unknown>");
    if ( !diagnostics_for_location.lookup_extended( file, null, out inner_table ) ) {
      inner_table = new HashTable< uint, BinarySearchDiagnosticArray >( direct_hash, direct_equal );
      diagnostics_for_location[ file ] = inner_table;
    }

    BinarySearchDiagnosticArray innermost_array;

    if ( !inner_table.lookup_extended( range.begin.line, null, out innermost_array ) ) {
      innermost_array = new BinarySearchDiagnosticArray( diagnostic );
      inner_table[ range.begin.line ] = innermost_array;
    } else
      innermost_array.add( diagnostic );
  }

  public Fix[] fix( int line,
                    int column,
                    HashTable< string, Bytes > unsaved_files,
                    bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      // TODO
      return new Fix[0];
    }
  }

  public Diagnostic? get_closest_diagnostic( Location location ) {
    HashTable< uint, BinarySearchDiagnosticArray > inner_table;
    BinarySearchDiagnosticArray innermost_array;

    if ( !diagnostics_for_location.lookup_extended( (!) location.file, null, out inner_table ) )
      return null;
    if ( !inner_table.lookup_extended( location.line, null, out innermost_array ) )
      return null;

    return innermost_array.find_nearest( location.column );
  }

  public Diagnostic[] get_diagnostics( uint max_num ) {
    uint num = uint.min( max_num, diagnostics.length );

    var result = new Diagnostic[num];
    for ( uint i = 0; i < num; i ++ )
      result[i] = diagnostics[i];

    return result;
  }

  public Documentation? get_documentation( int line,
                                           int column,
                                           HashTable< string, Bytes > unsaved_files,
                                           bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      var decl = Utils.get_declaration( node );

      if ( decl == null )
        return null;

      if ( !( decl is Vala.Symbol ) )
        return null;

      return new Documentation.vala((Vala.Symbol) decl);
    }
  }

  public string? get_expr_type( int line,
                                int column,
                                HashTable< string, Bytes > unsaved_files,
                                bool reparse = true,
                                bool debug = false ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      Vala.Scope? scope = null;
      var sym = Utils.find_enclosing_symbol( node );
      if ( sym != null )
        scope = ((!) sym).scope;

      Vala.DataType? type = null;

      if ( node is Vala.Expression ) {
        type = Utils.expression_type( (Vala.Expression) node );
      } else if ( node is Vala.DeclarationStatement ) {
        var declaration = ((Vala.DeclarationStatement) node).declaration;

        if ( declaration is Vala.Variable )
          type = ((Vala.Variable) declaration).variable_type;
      } else if ( node is Vala.Variable )
        type = ((Vala.Variable) node).variable_type;
      else if ( node is Vala.Property )
        type = ((Vala.Property) node).property_type;
      else if ( node is Vala.Callable )
        type = ((Vala.Method) node).return_type;
      else if ( node is Vala.DataType )
        type = (Vala.DataType) node;

      // For example a namespace reference
      if ( type == null )
        return null;

      var orig_type = type;

      if ( type is Vala.MethodType )
        type = ((Vala.MethodType) type).method_symbol.return_type;
      else if ( type is Vala.PropertyPrototype )
        type = ((Vala.PropertyPrototype) type).property_symbol.property_type;
      else if ( type is Vala.FieldPrototype )
        type = ((Vala.FieldPrototype) type).field_symbol.variable_type;

      if ( type == null )
        type = orig_type;

      var qual = ((!) type).to_qualified_string( scope );

      if ( debug )
        return "%s :: %s".printf( Type.from_instance( type ).name(), qual );
      else
        return qual;
    }
  }

  public string? get_parent( int line,
                             int column,
                             HashTable< string, Bytes > unsaved_files,
                             bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      Vala.Symbol? sym = Utils.find_parent_symbol( node );

      while ( sym != null && sym is Vala.Block )
        sym = Utils.find_parent_symbol( (!) sym );

      if ( sym == null )
        return null;

      return ((!) sym).get_full_name();
    }
  }

  public Location? go_to( int line,
                          int column,
                          HashTable< string, Bytes > unsaved_files,
                          bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      var decl = Utils.get_declaration( node );

      if ( decl == null )
        return null;

      return new Location.vala( (!) ((!) decl).source_reference );
    }
  }

  public Location? go_to_parent( int line,
                                 int column,
                                 HashTable< string, Bytes > unsaved_files,
                                 bool reparse = true ) throws CompleterError {
    lock( code_context ) {
      if ( reparse )
        this.reparse( unsaved_files );

      var loc = new Location( ((!) main_file).filename, line, column );

      if ( !loc.valid() )
        throw new CompleterError.INVALID_LOCATION(
          "Invalid location"
        );

      var node = Utils.get_node_by_location( (!) main_file, loc );

      Vala.Symbol? sym = Utils.find_parent_symbol( node );

      while ( sym != null && sym is Vala.Block )
        sym = Utils.find_parent_symbol( (!) sym );

      if ( sym == null )
        return null;

      return new Location.vala( (!) ((!) sym).source_reference );
    }
  }

  internal void register( HashTable< string, TranslationUnit > translation_unit_store ) throws CompleterError {
    foreach ( var source in ((!) code_context).get_source_files() )
      if ( source.from_commandline )
        translation_unit_store[ source.filename ] = this;
  }

  public void reparse( HashTable< string, Bytes > unsaved_files ) throws CompleterError {
    lock( code_context ) {
      diagnostics.length = 0;

      if ( code_context != null )
        code_context = null;

      code_context = flags.create_code_context( this );
      var code_context = (!) this.code_context;

      var pusher = new ContextPusher( code_context );
      pusher.use();

      if ( should_terminate() )
        return;

      foreach ( var file in code_context.get_source_files() ) {
        if ( file.filename == filename )
          main_file = file;

        Bytes? unsaved_nullable = null;
        if ( unsaved_files.lookup_extended( file.filename, null, out unsaved_nullable ) ) {
          var unsaved = (!) unsaved_nullable;
          size_t len = unsaved.get_size();
          var sb = new StringBuilder.sized( len + 2 );
          sb.append_len( (string) unsaved.get_data(), (ssize_t) len );
          if ( sb.len == 0 || sb.str[ sb.len - 1 ] != '\n' )
            sb.append_c( '\n' );
          file.content = sb.str;
        }
      }

      if ( main_file == null )
        throw new CompleterError.MAIN_FILE_NOT_IN_SOURCES(
          "Main file %s not mentioned in Vala sources", filename
        );

      new Vala.Parser().parse( code_context );
      new Vala.Genie.Parser().parse( code_context );
      new Vala.GirParser().parse( code_context );

      code_context.check();

      root_ns = code_context.root;
    }
  }

  private bool should_terminate() {
    var code_context = (!) this.code_context;
    var report = (Report) code_context.report;

    return report.should_terminate();
  }

  internal void unregister( HashTable< string, TranslationUnit > translation_unit_store ) {
    foreach ( var source in ((!) code_context).get_source_files() )
      if ( source.from_commandline )
        translation_unit_store.remove( source.filename );
  }

  public bool updating() {
    return false;
  }

  private class BinarySearchDiagnosticArray : Object {
    private GenericArray< Diagnostic > store;

    public BinarySearchDiagnosticArray( owned Diagnostic first_element ) {
      store = new GenericArray< Diagnostic >();
      store.add( first_element );
    }

    public void add( owned Diagnostic diag ) {
      store.insert( (int) find_right_index( diag.range.begin.column ), (owned) diag );
    }

    public Diagnostic find_nearest( uint column ) {
      uint rindex = find_right_index( column );

      if ( rindex == 0 )
        return store[ 0 ];

      var left = store[ rindex - 1 ];
      var right = store[ rindex ];

      if ( column - left.range.begin.column
           > right.range.begin.column - column )
        return right;
      else
        return left;
    }

    private uint find_right_index( uint column ) {
      // The actual binary search
      
      uint i = 0;
      uint j = store.length - 1;

      while ( i < j ) {
        uint mid = ( i + j ) / 2;

        var loc = store[ mid ].range.begin;
        if ( loc.column == column )
          return mid;
        else if ( loc.column > column ) {
          if ( mid == 0 )
            return 0;
          j = mid - 1;
        } else if ( mid == store.length - 1
                    || store[ mid + 1 ].range.begin.column > column ) {
          if ( mid == store.length - 1
               && loc.column < column )
            return store.length;
          else
            return mid;
        } else
          i = mid + 1;
      }

      return i;
    }
  }

  private class ContextPusher {
    public ContextPusher( Vala.CodeContext code_context ) {
      Vala.CodeContext.push( code_context );
    }

    ~ContextPusher() {
      Vala.CodeContext.pop();
    }

    public void use() {
      // Suppress unused warning
    }
  }

  internal class Report : Vala.Report {
    public bool fatal_warnings { get; private set; }
    public TranslationUnit tu { get; private set; }

    public Report( TranslationUnit tu,
                   bool fatal_warnings = false ) {
      base();
      this.fatal_warnings = fatal_warnings;
      this.tu = tu;
    }

    public override void depr( Vala.SourceReference? source,
                               string message ) {
      tu.diagnostic_add( DiagnosticKind.DEPRECATION_WARNING,
                         source == null ? new Range.invalid() : new Range.vala( (!) source ),
                         message,
                         tu.can_fix( message ) );
    }

    public override void err( Vala.SourceReference? source,
                              string message ) {
      tu.diagnostic_add( DiagnosticKind.ERROR,
                         source == null ? new Range.invalid() : new Range.vala( (!) source ),
                         message,
                         tu.can_fix( message ) );
    }

    public override void note( Vala.SourceReference? source,
                               string message ) {
      tu.diagnostic_add( DiagnosticKind.NOTICE,
                         source == null ? new Range.invalid() : new Range.vala( (!) source ),
                         message,
                         tu.can_fix( message ) );
    }

    public bool should_terminate() {
      return errors > 0 || (fatal_warnings && warnings > 0);
    }

    public override void warn( Vala.SourceReference? source,
                               string message ) {
      tu.diagnostic_add( DiagnosticKind.WARNING,
                         source == null ? new Range.invalid() : new Range.vala( (!) source ),
                         message,
                         tu.can_fix( message ) );
    }
  }
}

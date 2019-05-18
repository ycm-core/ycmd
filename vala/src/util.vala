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

using Vala;

namespace Ycmvala.Utils {
  internal DataType expression_target_type( Expression expr ) {
    DataType? type = expr.formal_target_type;

    if ( type == null )
      type = expr.target_type;

    return (!) type;
  }

  internal DataType expression_type( Expression expr ) {
    DataType? type = expr.formal_value_type;

    if ( type == null )
      type = expr.value_type;

    return (!) type;
  }

  internal Symbol? find_enclosing_symbol( CodeNode node ) {
    CodeNode? cn_iter = node;

    while ( cn_iter != null && !( cn_iter is Symbol ) )
      cn_iter = ((!) cn_iter).parent_node;

    return (Symbol?) cn_iter;
  }

  internal Symbol? find_parent_symbol( CodeNode node ) {
    if ( node is Symbol )
        return ((Symbol) node).parent_symbol;
    else
      return find_enclosing_symbol( node );
  }

  internal delegate bool ForEachSymbolFunc( string key,
                                            Symbol symbol );

  internal bool for_each_symbol( Scope scope,
                                 ForEachSymbolFunc func,
                                 bool recursive = true ) {
      while ( scope != (Scope) null ) {
        if ( scope.get_symbol_table() != (Vala.Map< string, Symbol >) null ) {
          var iter = scope.get_symbol_table().map_iterator();
          while ( iter.next() )
            if ( !func( iter.get_key(), iter.get_value() ) )
              return false;
        }

        scope = scope.parent_scope;
      }

      return true;
  }

  private class GetDeclarationVisitor : CodeVisitor {
    private CodeNode? result = null;

    public GetDeclarationVisitor() {
      base();
    }

    internal CodeNode? run( CodeNode node ) {
      node.accept( this );
      return (owned) result;
    }

    public override void visit_addressof_expression( AddressofExpression expr ) {
      expr.inner.accept( this );
    }

    public override void visit_array_creation_expression( ArrayCreationExpression expr ) {
      expr.element_type.accept( this );
    }

    public override void visit_assignment( Assignment a ) {
      a.left.accept( this );
    }

    public override void visit_cast_expression( CastExpression expr ) {
      expr.inner.accept( this );
    }

    public override void visit_catch_clause( CatchClause clause ) {
      if ( clause.error_type != null )
        ((!) clause.error_type).accept( this );
    }

    public override void visit_class( Class cl ) {
      result = cl;
    }

    public override void visit_constant( Constant c ) {
      result = c;
    }

    public override void visit_constructor( Constructor c ) {
      result = c;
    }

    public override void visit_creation_method( CreationMethod m ) {
      result = m;
    }

    public override void visit_data_type( DataType type ) {
      if ( type is ArrayType )
        ((ArrayType) type).element_type.accept( this );
      else if ( type is ClassType )
        ((ClassType) type).class_symbol.accept( this );
      else if ( type is DelegateType )
        ((DelegateType) type).delegate_symbol.accept( this );
      else if ( type is Vala.ErrorType )
        ((!) ((Vala.ErrorType) type).error_code).accept( this );
      else if ( type is FieldPrototype )
        ((FieldPrototype) type).field_symbol.accept( this );
      else if ( type is GenericType )
        ((GenericType) type).type_parameter.accept( this );
      else if ( type is InterfaceType )
        ((InterfaceType) type).interface_symbol.accept( this );
      else if ( type is ObjectType )
        ((ObjectType) type).type_symbol.accept( this );
      else if ( type is PointerType )
        ((PointerType) type).base_type.accept( this );
      else if ( type is SignalType )
        ((SignalType) type).signal_symbol.accept( this );
      else if ( type is UnresolvedType )
        ((UnresolvedType) type).unresolved_symbol.accept( this );
      else if ( type is ValueType )
        ((ValueType) type).type_symbol.accept( this );
    }

    public override void visit_delegate( Delegate d ) {
      result = d;
    }

    public override void visit_destructor( Destructor d ) {
      result = d;
    }

    public override void visit_element_access( ElementAccess expr ) {
      expr.container.accept( this );
    }

    public override void visit_enum( Enum en ) {
      result = en;
    }

    public override void visit_enum_value( Vala.EnumValue ev ) {
      result = ev;
    }

    public override void visit_error_code( ErrorCode ecode ) {
      result = ecode;
    }

    public override void visit_error_domain( ErrorDomain edomain ) {
      result = edomain;
    }

    public override void visit_expression( Expression expr ) {
      if ( result == null )
        result = expr.symbol_reference;
      if ( result == null )
        result = expression_type( expr );
    }

    public override void visit_field( Field f ) {
      result = f;
    }

    public override void visit_formal_parameter( Vala.Parameter p ) {
      result = p;
    }

    public override void visit_interface( Interface iface ) {
      result = iface;
    }

    public override void visit_lambda_expression( LambdaExpression expr ) {
      expression_target_type( expr ).accept( this );
    }

    public override void visit_local_variable( LocalVariable local ) {
      result = local;
    }

    public override void visit_lock_statement( LockStatement stmt ) {
      stmt.resource.accept( this );
    }

    public override void visit_member_access( MemberAccess expr ) {
      var vt = expression_type( expr );
      if ( vt.get_member( expr.member_name ) != null )
        ((!) vt.get_member( expr.member_name ) ).accept( this );
    }

    public override void visit_method( Method m ) {
      result = m;
    }

    public override void visit_method_call( MethodCall expr ) {
      expr.call.accept( this );
    }

    public override void visit_named_argument( NamedArgument expr ) {
      expr.inner.accept( this );
    }

    public override void visit_namespace( Namespace ns ) {
      result = ns;
    }

    public override void visit_object_creation_expression( ObjectCreationExpression expr ) {
      expr.type_reference.accept( this );
    }

    public override void visit_pointer_indirection( PointerIndirection expr ) {
      expr.inner.accept( this );
    }

    public override void visit_postfix_expression( PostfixExpression expr ) {
      expr.inner.accept( this );
    }

    public override void visit_property( Property prop ) {
      result = prop;
    }

    public override void visit_property_accessor( PropertyAccessor acc ) {
      result = acc;
    }

    public override void visit_reference_transfer_expression( ReferenceTransferExpression expr ) {
      expr.inner.accept( this );
    }

    public override void visit_return_statement( ReturnStatement stmt ) {
      if ( stmt.return_expression != null )
        ((!) stmt.return_expression).accept( this );
    }

    public override void visit_signal( Vala.Signal sig ) {
      result = sig;
    }

    public override void visit_sizeof_expression( SizeofExpression expr ) {
      expr.type_reference.accept( this );
    }

    public override void visit_slice_expression( SliceExpression expr ) {
      expr.container.accept( this );
    }

    public override void visit_struct( Struct st ) {
      result = st;
    }

    public override void visit_switch_label( SwitchLabel label ) {
      label.expression.accept( this );
    }

    public override void visit_switch_statement( SwitchStatement stmt ) {
      stmt.expression.accept( this );
    }

    public override void visit_throw_statement( ThrowStatement stmt ) {
      stmt.error_expression.accept( this );
    }

    public override void visit_type_check( TypeCheck expr ) {
      expr.expression.accept( this );
    }

    public override void visit_type_parameter( TypeParameter p ) {
      result = p;
    }

    public override void visit_typeof_expression( TypeofExpression expr ) {
      expr.type_reference.accept( this );
    }

    public override void visit_unary_expression( UnaryExpression expr ) {
      expr.inner.accept( this );
    }

    public override void visit_unlock_statement( UnlockStatement stmt ) {
      stmt.resource.accept( this );
    }

    public override void visit_using_directive( UsingDirective ns ) {
      ns.namespace_symbol.accept( this );
    }

    public override void visit_while_statement( WhileStatement stmt ) {
      stmt.condition.accept( this );
    }
  }

  internal CodeNode? get_declaration( CodeNode node ) {
    return new GetDeclarationVisitor().run( node );
  }

  private class GetNodeByLocationVisitor : CodeVisitor {
    public SourceFile file { get; private set; }
    public Location location { get; private set; }
    private CodeNode? result = null;

    public GetNodeByLocationVisitor( SourceFile file,
                                     Location location ) {
      base();
      this.file = file;
      this.location = location;
    }

    internal CodeNode? run() {
      file.accept( this );
      return (owned) result;
    }

    private void recurse( CodeNode node ) {
      if ( node is PropertyAccessor
           && ((PropertyAccessor) node).automatic_body ) {
      } else if ( node is MemberAccess ) {
        var expr = (Vala.MemberAccess) node;
        if ( expr.source_reference != null
             && expr.inner != null
             && ((!) expr.inner).source_reference != null
             && ((!) expr.source_reference).end.pos
                == ((!) ((!) expr.inner).source_reference).end.pos )
          // Implicit constructor
          return;
        else
          node.accept_children( this );
      } else
        node.accept_children( this );
    }

    private void visit( CodeNode node ) {
      if ( result != null )
        return;

      var ref = node.source_reference;

      if ( ref == null )
        return;

      if ( ((!) ref).file != file )
        return;

      recurse( node );

      if ( result != null )
        return;

      if ( !source_reference_contains( (!) ref, location.to_vala() ) )
        return;

      result = node;
    }

    public override void visit_addressof_expression( AddressofExpression expr ) { visit( expr ); }
    public override void visit_array_creation_expression( ArrayCreationExpression expr ) { visit( expr ); }
    public override void visit_assignment( Assignment a ) { visit( a ); }
    public override void visit_base_access( BaseAccess expr ) { visit( expr ); }
    public override void visit_binary_expression( BinaryExpression expr ) { visit( expr ); }
    public override void visit_block( Block b ) { visit( b ); }
    public override void visit_boolean_literal( BooleanLiteral lit ) { visit( lit ); }
    public override void visit_break_statement( BreakStatement stmt ) { visit( stmt ); }
    public override void visit_cast_expression( CastExpression expr ) { visit( expr ); }
    public override void visit_catch_clause( CatchClause clause ) { visit( clause ); }
    public override void visit_character_literal( CharacterLiteral lit ) { visit( lit ); }
    public override void visit_class( Class cl ) { visit( cl ); }
    public override void visit_conditional_expression( ConditionalExpression expr ) { visit( expr ); }
    public override void visit_constant( Constant c ) { visit( c ); }

    public override void visit_constructor( Constructor c ) {
      if ( c.source_reference != null
           && c.parent_symbol != null
           && ((!) c.parent_symbol).source_reference != null
           && ((!) c.source_reference).begin.pos
              == ((!) ((!) c.parent_symbol).source_reference).begin.pos )
        // Implicit constructor
        return;

      visit( c );
    }

    public override void visit_continue_statement( ContinueStatement stmt ) { visit( stmt ); }

    public override void visit_creation_method( CreationMethod m ) {
      if ( m.source_reference != null
           && m.parent_symbol != null
           && ((!) m.parent_symbol).source_reference != null
           && ((!) m.source_reference).begin.pos
              == ((!) ((!) m.parent_symbol).source_reference).begin.pos )
        // Implicit constructor
        return;

      visit( m );
    }

    public override void visit_data_type( DataType type ) { visit( type ); }
    public override void visit_declaration_statement( DeclarationStatement stmt ) { visit( stmt ); }
    public override void visit_delegate( Delegate d ) { visit( d ); }
    public override void visit_delete_statement( DeleteStatement stmt ) { visit( stmt ); }
    public override void visit_destructor( Destructor d ) { visit( d ); }
    public override void visit_do_statement( DoStatement stmt ) { visit( stmt ); }
    public override void visit_element_access( ElementAccess expr ) { visit( expr ); }
    public override void visit_empty_statement( EmptyStatement stmt ) { visit( stmt ); }
    public override void visit_end_full_expression( Expression expr ) { visit( expr ); }
    public override void visit_enum( Enum en ) { visit( en ); }
    public override void visit_enum_value( Vala.EnumValue ev ) { visit( ev ); }
    public override void visit_error_code( ErrorCode ecode ) { visit( ecode ); }
    public override void visit_error_domain( ErrorDomain edomain ) { visit( edomain ); }
    public override void visit_expression( Expression expr ) { visit( expr ); }
    public override void visit_expression_statement( ExpressionStatement stmt ) { visit( stmt ); }

    public override void visit_field( Field f ) {
      unowned string name = (!) f.name;

      if ( f.parent_symbol is Class ) {
        if ( name[0] == '_' ) {
          unowned string prop_name = (string) ((char *) name + 1);
          var parent = (Class) f.parent_symbol;

          var member = parent.get_this_type().get_member( prop_name );

          if ( member != null && ((!) member) is Property ) {
            var prop = (Property) (!) member;

            if ( prop.field == f )
              // Generated field
              return;
          }
        }
      }
      visit( f );
    }

    public override void visit_for_statement( ForStatement stmt ) { visit( stmt ); }
    public override void visit_foreach_statement( ForeachStatement stmt ) { visit( stmt ); }
    public override void visit_formal_parameter( Vala.Parameter p ) { visit( p ); }
    public override void visit_if_statement( IfStatement stmt ) { visit( stmt ); }
    public override void visit_initializer_list( InitializerList list ) { visit( list ); }
    public override void visit_integer_literal( IntegerLiteral lit ) { visit( lit ); }
    public override void visit_interface( Interface iface ) { visit( iface ); }
    public override void visit_lambda_expression( LambdaExpression expr ) { visit( expr ); }
    public override void visit_local_variable( LocalVariable local ) { visit( local ); }
    public override void visit_lock_statement( LockStatement stmt ) { visit( stmt ); }
    public override void visit_loop( Loop stmt ) { visit( stmt ); }
    public override void visit_member_access( MemberAccess expr ) {
      visit( expr );
    }
    public override void visit_method( Method m ) { visit( m ); }
    public override void visit_method_call( MethodCall expr ) { visit( expr ); }
    public override void visit_named_argument( NamedArgument expr ) { visit( expr ); }
    public override void visit_namespace( Namespace ns ) { visit( ns ); }
    public override void visit_null_literal( NullLiteral lit ) { visit( lit ); }
    public override void visit_object_creation_expression( ObjectCreationExpression expr ) { visit( expr ); }
    public override void visit_pointer_indirection( PointerIndirection expr ) { visit( expr ); }
    public override void visit_postfix_expression( PostfixExpression expr ) { visit( expr ); }
    public override void visit_property( Property prop ) { visit( prop ); }
    public override void visit_property_accessor( PropertyAccessor acc ) { visit( acc ); }
    public override void visit_real_literal( RealLiteral lit ) { visit( lit ); }
    public override void visit_reference_transfer_expression( ReferenceTransferExpression expr ) { visit( expr ); }
    public override void visit_regex_literal( RegexLiteral lit ) { visit( lit ); }
    public override void visit_return_statement( ReturnStatement stmt ) { visit( stmt ); }
    public override void visit_signal( Vala.Signal sig ) { visit( sig ); }
    public override void visit_sizeof_expression( SizeofExpression expr ) { visit( expr ); }
    public override void visit_slice_expression( SliceExpression expr ) { visit( expr ); }
    public override void visit_source_file( SourceFile file ) { file.accept_children( this ); }
    public override void visit_string_literal( StringLiteral lit ) { visit( lit ); }
    public override void visit_struct( Struct st ) { visit( st ); }
    public override void visit_switch_label( SwitchLabel label ) { visit( label ); }
    public override void visit_switch_section( SwitchSection section ) { visit( section ); }
    public override void visit_switch_statement( SwitchStatement stmt ) { visit( stmt ); }
    public override void visit_template( Template tmpl ) { visit( tmpl ); }
    public override void visit_throw_statement( ThrowStatement stmt ) { visit( stmt ); }
    public override void visit_try_statement( TryStatement stmt ) { visit( stmt ); }
    public override void visit_tuple( Tuple tuple ) { visit( tuple ); }
    public override void visit_type_check( TypeCheck expr ) { visit( expr ); }
    public override void visit_type_parameter( TypeParameter p ) { visit( p ); }
    public override void visit_typeof_expression( TypeofExpression expr ) { visit( expr ); }
    public override void visit_unary_expression( UnaryExpression expr ) { visit( expr ); }
    public override void visit_unlock_statement( UnlockStatement stmt ) { visit( stmt ); }
    public override void visit_using_directive( UsingDirective ns ) { visit( ns ); }
    public override void visit_while_statement( WhileStatement stmt ) { visit( stmt ); }
    public override void visit_yield_statement( YieldStatement y ) { visit( y ); }
  }

  internal CodeNode get_node_by_location( SourceFile file,
                                          Location location ) throws CompleterError {
    var node = new GetNodeByLocationVisitor( file, location ).run();

    if ( node != null )
      return (!) node;
    else
      throw new CompleterError.NODE_NOT_FOUND(
        "Cannot find node at location"
      );
  }

  internal bool source_location_le( SourceLocation left,
                                    SourceLocation right ) {
    if ( left.line > right.line )
      return false;
    if ( left.line < right.line )
      return true;
    return left.column <= right.column;
  }

  internal bool source_reference_contains( SourceReference reference,
                                           SourceLocation location ) {
    // Assumption: the file matches
    
    return source_location_le( reference.begin, location )
      && source_location_le( location, reference.end );
  }
}

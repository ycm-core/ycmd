// SIMPLE FUNCITONS

function no_arguments_no_return() {
}

interface ReturnValue {
  a: string;
  b: number;
};

function no_arguments_with_return() : ReturnValue {
  return {
    a: 'test',
    b: 100
  };
}

function single_argument_no_return( a: string ) {
  return 's';
}

function single_argument_with_return( a: string ) : string {
  return 's';
}

no_arguments_no_return();
single_argument_with_return(
  single_argument_no_return(
    no_arguments_with_return().a
  )
)

// CLASSES

class SomeClass implements ReturnValue {
  a: string;
  b: number;

  constructor( public a_: string,
               public b_: string ) {
    this.a = a_;
    this.b = parseInt( b_ );
  }

  public Test( c: number ) : number {
    return this.b * c;
  }
  public TestAgain( d ) : number {
    return this.b * d;
  }
};

function multi_argument_no_return(
  løng_våriable_name: number,
  untyped_argument ) {
  var c = new SomeClass( untyped_argument,
                         løng_våriable_name.toString() );
  return c.Test( 10 );
}
multi_argument_no_return( 1000, 'test' );

// GENERICS

function generic<TYPE extends ReturnValue>( t: TYPE ): string {
  return t.a;
}

generic<SomeClass>( new SomeClass( 'a', '1' ) );

// OVERLOADS

function overload_fake( a: string | number,
                        b : string ) : boolean | string {
  if ( typeof a === 'string' ) {
    return true;
  } else {
    return b;
  }
}

overload_fake( 1, 'two' )

function øverløåd( a: number ) : string;
function øverløåd( a: string, b :number ) : string;
function øverløåd( a: string | number, b: number = 1 ) : string {
  return '1';
}

øverløåd( 'a', 1 );
øverløåd( 1 );

dod(

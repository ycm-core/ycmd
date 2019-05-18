public void alpha_incr( char[] chars ) {
  uint i = chars.length - 1;

  while ( i > 0 )
    if ( chars[ i - 1 ] == 'z' )
      chars[  --i ] = 'a';
    else {
      chars[ i - 1 ] ++;
      break;
    }
}

public uint powsmallint( uint @base,
                         uint exp ) {
  uint res = 1;
  while ( ( exp-- ) > 0 )
    res *= @base;
  return res;
}

public void generate_n( uint n ) throws Error {
  char[] buf = new char[n + 1];
  Memory.@set( buf, 'a', n );
  buf[ n ] = '\0';

  var f = File.new_for_path( "benchmarks/methods%u.vala".printf( n ) );
  var fout = f.replace( null, false, FileCreateFlags.REPLACE_DESTINATION );
  var @out = new DataOutputStream( new BufferedOutputStream.sized( fout, 1024 * 1024 ) );

  @out.put_string( "public class Large {\n" );

  if ( n == 0 )
    @out.put_string( "  public void a() {}\n" );
  else {
    var max = powsmallint( 26, n );

    for ( uint i = 0; i < max; i ++ ) {
      @out.put_string( " public void " );

      if ( unlikely( unlikely( i == 389386 ) && n == 4 ) )
        @out.put_byte( '@' );

      @out.put_string( (string) buf );
      @out.put_string( "() {}\n" );
      alpha_incr( buf );
    }
  }

  @out.put_string( "}\n" );

  @out.close();
}

public const uint MAX_LENGTH = 3;

public int main() {
  try {
    for ( uint length = 0; length <= MAX_LENGTH; length ++ )
      generate_n( length );
    return 0;
  } catch ( Error error ) {
    printerr( "Error: %s\n", error.message );
    return 1;
  }
}

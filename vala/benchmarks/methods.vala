public delegate void Runnable() throws Ycmvala.CompleterError;

public double avg_time( Runnable r, double max_time, out uint64 runs_out ) throws Ycmvala.CompleterError {
  var timer_pertask = new Timer();
  var times = new GenericArray< ulong >();
  uint64 runs = 0;

  int64 limit = get_monotonic_time() + (int64) (max_time * 1000000);

  while ( get_monotonic_time() < limit ) {
    timer_pertask.start();
    r();
    times.add( (ulong) ( timer_pertask.elapsed() * 1048576 ) );
    runs ++;
  }

  runs_out = runs;
  if ( times.length == 0 )
    return 0.0;
  double sum = times[ 0 ];
  for ( uint i = 1; i < times.length; i ++ )
    sum += times[ i ];
  sum /= 1048576;
  return sum / times.length;
}

public struct Benchmark {
  uint n;
  double time;
}

public const Benchmark[] BENCHMARKS = {
  { 0,  5.0 },
  { 1,  5.0 },
  { 2,  5.0 },
  { 3,  5.0 }
};

public void benchmark_complete( Benchmark bench ) throws Ycmvala.CompleterError {
  var unsaved = new HashTable< string, Bytes >( str_hash, str_equal );
  var completer = new Ycmvala.Completer();
  var fname = Vala.CodeContext.realpath( "benchmarks/methods%u.vala".printf( bench.n ) );
  var tu = completer.get_translation_unit( fname, unsaved, new string[] { "valac", fname }, null );

  uint64 runs;
  var avg = avg_time( () => {
    tu.complete( 2, 3, unsaved, false );
    tu.complete_with_prefix( 2, 3, "a", unsaved, false );
    tu.complete_with_prefix( 2, 3, "aa", unsaved, false );
    tu.complete_with_prefix( 2, 3, "aaa", unsaved, false );
    tu.complete_with_prefix( 2, 3, "aaaa", unsaved, false );
    tu.complete_with_prefix( 2, 3, "aaaaa", unsaved, false );
  }, bench.time, out runs );

  stdout.printf( "Complete[%u] : avg %lf runs %" + uint64.FORMAT + "\n", bench.n, avg, runs );
  stdout.flush();
}

public void main() {
  foreach ( var bench in BENCHMARKS )
    benchmark_complete( bench );
}

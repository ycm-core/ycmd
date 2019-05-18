public void test_simple() {
  var completer = new Ycmvala.Completer();
  var files = new HashTable< string, Bytes >( str_hash, str_equal );
  var fpath = Vala.CodeContext.realpath( "tests/simple.vala" );
  var tu = completer.get_translation_unit( fpath, files, new string[] { "valac", fpath }, null );
  var results = tu.complete_with_prefix( 11, 14, "xyzxyzxyz", files, false );
  assert_true (results.length == 5);
  assert_true (results[0].insertion_text == "xyzxyzxyzenum");
  assert_true (results[1].insertion_text == "xyzxyzxyzfield");
  assert_true (results[2].insertion_text == "xyzxyzxyzmethod");
  assert_true (results[3].insertion_text == "xyzxyzxyzproperty");
  assert_true (results[4].insertion_text == "xyzxyzxyzsig");
}

public int main( string[] args ) {
  Test.init( ref args );

  Test.add_func( "/Ycmvala/complete/simple", test_simple );

  return Test.run();
}

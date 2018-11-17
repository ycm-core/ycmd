class ExtraConf {
  public ExtraConf( int test ) {}

  public static void main( String[] args ) {
    ExtraConf l = new ExtraConf( 10 );
    ExtraConf t = new ExtraConf( 4 );
    l = t;
    t = l;
  }
}

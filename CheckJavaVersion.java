class CheckJavaVersion
{
  public static void main( String[] args )
  {
    int featureVersion = java.lang.Runtime.version().feature();
    System.out.println( featureVersion );
  }
}

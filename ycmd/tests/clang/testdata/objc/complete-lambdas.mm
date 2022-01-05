/* Modified by ycmd contributors */
// This test is line- and column-sensitive. See below for run lines.


@interface A
- instanceMethod:(int)value withOther:(int)other;
+ classMethod;
@end

@interface B : A
@end

@implementation B
- someMethod:(A*)a {
  [a classMethod];
  [A classMethod];
  [a instanceMethod:0 withOther:1];
  [self someMethod:a];
  [super instanceMethod];
  [&,a ]{};
  [a,self instanceMethod:0 withOther:1]{};
}

@end

// Copyright (C) 2011-2018 ycmd contributors
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

#include "Candidate.h"
#include "Result.h"

#include <gtest/gtest.h>
#include <gmock/gmock.h>

using ::testing::Not;

namespace YouCompleteMe {

MATCHER_P( HasWordBoundaryCharacters,
           boundary_chars,
           std::string( negation ? "has not" : "has" ) +
           " word boundary characters " + boundary_chars ) {
  return Candidate( arg ).WordBoundaryChars() ==
         Word( boundary_chars ).Characters();
}

TEST( WordBoundaryCharsTest, SimpleOneWord ) {
  EXPECT_THAT( "simple", HasWordBoundaryCharacters( "s" ) );
}

TEST( WordBoundaryCharsTest, PunctuationInMiddle ) {
  EXPECT_THAT( "simple_foo", HasWordBoundaryCharacters( "sf" ) );
}

TEST( WordBoundaryCharsTest, PunctuationStart ) {
  EXPECT_THAT( "_simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( ".simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( "/simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( ":simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( "-simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( "«simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( "…simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( "𐬺simple", HasWordBoundaryCharacters( "s" ) );
}

TEST( WordBoundaryCharsTest, PunctuationStartButFirstDigit ) {
  EXPECT_THAT( "_1simple", HasWordBoundaryCharacters( ""  ) );
  EXPECT_THAT( "_1simPle", HasWordBoundaryCharacters( "P" ) );
  EXPECT_THAT( "…𝟝simple", HasWordBoundaryCharacters( ""  ) );
  EXPECT_THAT( "…𝟝simPle", HasWordBoundaryCharacters( "P" ) );
}

TEST( WordBoundaryCharsTest, ManyPunctuationStart ) {
  EXPECT_THAT( "___simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( ".;/simple", HasWordBoundaryCharacters( "s" ) );
  EXPECT_THAT( "«…𐬺simple", HasWordBoundaryCharacters( "s" ) );
}

TEST( WordBoundaryCharsTest, PunctuationStartAndInMiddle ) {
  EXPECT_THAT( "_simple_foo", HasWordBoundaryCharacters( "sf" ) );
  EXPECT_THAT( "/simple.foo", HasWordBoundaryCharacters( "sf" ) );
  EXPECT_THAT( "𐬺simple—foo", HasWordBoundaryCharacters( "sf" ) );
}

TEST( WordBoundaryCharsTest, ManyPunctuationStartAndInMiddle ) {
  EXPECT_THAT( "___simple__foo",  HasWordBoundaryCharacters( "sf" ) );
  EXPECT_THAT( "./;:simple..foo", HasWordBoundaryCharacters( "sf" ) );
  EXPECT_THAT( "«𐬺…simple——foo",  HasWordBoundaryCharacters( "sf" ) );
}

TEST( WordBoundaryCharsTest, SimpleCapitalStart ) {
  EXPECT_THAT( "Simple", HasWordBoundaryCharacters( "S" ) );
  EXPECT_THAT( "Σimple", HasWordBoundaryCharacters( "Σ" ) );
}

TEST( WordBoundaryCharsTest, SimpleCapitalTwoWord ) {
  EXPECT_THAT( "SimpleStuff", HasWordBoundaryCharacters( "SS" ) );
  EXPECT_THAT( "ΣimpleΣtuff", HasWordBoundaryCharacters( "ΣΣ" ) );
}

TEST( WordBoundaryCharsTest, SimpleCapitalTwoWordPunctuationMiddle ) {
  EXPECT_THAT( "Simple_Stuff", HasWordBoundaryCharacters( "SS" ) );
  EXPECT_THAT( "Σimple…Σtuff", HasWordBoundaryCharacters( "ΣΣ" ) );
}

TEST( WordBoundaryCharsTest, JavaCase ) {
  EXPECT_THAT( "simpleStuffFoo", HasWordBoundaryCharacters( "sSF" ) );
  EXPECT_THAT( "σimpleΣtuffΦoo", HasWordBoundaryCharacters( "σΣΦ" ) );
}

TEST( WordBoundaryCharsTest, UppercaseSequence ) {
  EXPECT_THAT( "simpleSTUFF", HasWordBoundaryCharacters( "sS" ) );
  EXPECT_THAT( "σimpleΣTUFF", HasWordBoundaryCharacters( "σΣ" ) );
}

TEST( WordBoundaryCharsTest, UppercaseSequenceInMiddle ) {
  EXPECT_THAT( "simpleSTUFFfoo", HasWordBoundaryCharacters( "sS" ) );
  EXPECT_THAT( "σimpleΣTUFFφoo", HasWordBoundaryCharacters( "σΣ" ) );
}

TEST( WordBoundaryCharsTest, UppercaseSequenceInMiddlePunctuation ) {
  EXPECT_THAT( "simpleSTUFF_Foo", HasWordBoundaryCharacters( "sSF" ) );
  EXPECT_THAT( "σimpleΣTUFF…Φoo", HasWordBoundaryCharacters( "σΣΦ" ) );
}

TEST( WordBoundaryCharsTest, UppercaseSequenceInMiddlePunctuationLowercase ) {
  EXPECT_THAT( "simpleSTUFF_foo", HasWordBoundaryCharacters( "sSf" ) );
  EXPECT_THAT( "simpleSTUFF.foo", HasWordBoundaryCharacters( "sSf" ) );
  EXPECT_THAT( "σimpleΣTUFF…φoo", HasWordBoundaryCharacters( "σΣφ" ) );
}

TEST( WordBoundaryCharsTest, AllCapsSimple ) {
  EXPECT_THAT( "SIMPLE", HasWordBoundaryCharacters( "S" ) );
  EXPECT_THAT( "ΣIMPLE", HasWordBoundaryCharacters( "Σ" ) );
}

TEST( GetWordBoundaryCharsTest, AllCapsPunctuationStart ) {
  EXPECT_THAT( "_SIMPLE", HasWordBoundaryCharacters( "S" ) );
  EXPECT_THAT( ".SIMPLE", HasWordBoundaryCharacters( "S" ) );
  EXPECT_THAT( "«ΣIMPLE", HasWordBoundaryCharacters( "Σ" ) );
  EXPECT_THAT( "…ΣIMPLE", HasWordBoundaryCharacters( "Σ" ) );
}

TEST( WordBoundaryCharsTest, AllCapsPunctuationMiddle ) {
  EXPECT_THAT( "SIMPLE_STUFF", HasWordBoundaryCharacters( "SS" ) );
  EXPECT_THAT( "SIMPLE/STUFF", HasWordBoundaryCharacters( "SS" ) );
  EXPECT_THAT( "SIMPLE—ΣTUFF", HasWordBoundaryCharacters( "SΣ" ) );
  EXPECT_THAT( "ΣIMPLE…STUFF", HasWordBoundaryCharacters( "ΣS" ) );
}

TEST( WordBoundaryCharsTest, AllCapsPunctuationMiddleAndStart ) {
  EXPECT_THAT( "_SIMPLE_STUFF", HasWordBoundaryCharacters( "SS" ) );
  EXPECT_THAT( ":SIMPLE.STUFF", HasWordBoundaryCharacters( "SS" ) );
  EXPECT_THAT( "«ΣIMPLE—ΣTUFF", HasWordBoundaryCharacters( "ΣΣ" ) );
  EXPECT_THAT( "𐬺SIMPLE—ΣTUFF", HasWordBoundaryCharacters( "SΣ" ) );
}

TEST( CandidateTest, TextValid ) {
  EXPECT_EQ( "foo", Candidate( "foo" ).Text() );
}

MATCHER_P( IsSubsequence,
           candidate,
           std::string( negation ? "is not" : "is" ) + " a subsequence of " +
           candidate ) {
  Result result = Candidate( candidate ).QueryMatchResult( Word( arg ) );
  return result.IsSubsequence();
}

TEST( CandidateTest, QueryMatchResultIsSubsequence ) {
  EXPECT_THAT( "F𐍈oβaÅAr", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "FβÅA",     IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "F",        IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "ÅA",       IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "A",        IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "β",        IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f𐍈oβaåar", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f𐍈oβaåAr", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f𐍈oβaÅar", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f𐍈oβaÅAr", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "F𐍈oβaÅAr", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f𐍈oβaaar", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f𐍈oβaAar", IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "fβÅA",     IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "fβaa",     IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "β",        IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "f",        IsSubsequence( "F𐍈oβaÅAr" ) );
  EXPECT_THAT( "fβår",     IsSubsequence( "F𐍈oβaÅAr" ) );
}

TEST( CandidateTest, QueryMatchResultIsNotSubsequence ) {
  EXPECT_THAT( "g𐍈o",      Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "R",        Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "O",        Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "𐍈O",       Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "OβA",      Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "FβAR",     Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "FβÅAR",    Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "Oar",      Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈oβaÅår", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈oβaåår", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈oβaÅÅr", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈oβaåÅr", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "f𐍈oβaÅÅr", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈oβaaÅr", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈OβaÅAr", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "F𐍈Oβaåar", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "f𐍈Oβaåar", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
  EXPECT_THAT( "f𐍈oβaåaR", Not( IsSubsequence( "F𐍈oβaÅAr" ) ) );
}

} // namespace YouCompleteMe

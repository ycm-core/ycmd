// Copyright (C) 2018 ycmd contributors
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

#include "CharacterRepository.h"
#include "CodePoint.h"
#include "Word.h"

#include <string>

namespace YouCompleteMe {

namespace {

// Break a sequence of code points into characters (grapheme clusters) according
// to the rules in
// https://www.unicode.org/reports/tr29/#Grapheme_Cluster_Boundary_Rules
std::vector< std::string > BreakCodePointsIntoCharacters(
  const CodePointSequence &code_points ) {

  std::vector< std::string > characters;

  // Rules GB1 and GB2 (break at the start and at the end of the text) are
  // automatically satisfied.

  auto code_point_pos = code_points.begin();
  if ( code_point_pos == code_points.end() ) {
    return characters;
  }

  std::string character;
  character.append( ( *code_point_pos )->Normal() );

  auto previous_code_point_pos = code_point_pos;
  ++code_point_pos;
  if ( code_point_pos == code_points.end() ) {
    characters.push_back( character );
    return characters;
  }

  bool is_regional_indicator_nb_odd = false;
  bool within_emoji_modifier = false;

  for ( ; code_point_pos != code_points.end() ; ++previous_code_point_pos,
                                                ++code_point_pos ) {
    auto previous_property = ( *previous_code_point_pos )->GetBreakProperty();
    const auto &code_point = ( *code_point_pos )->Normal();
    auto property = ( *code_point_pos )->GetBreakProperty();

    switch( previous_property ) {
      case BreakProperty::CR:
        switch( property ) {
          // Rule GB3: do not break between a CR and LF.
          case BreakProperty::LF:
            character.append( code_point );
            break;
          // Rule GB4: otherwise, break after CR.
          default:
            characters.push_back( character );
            character = code_point;
        }
        break;
      // Rule GB4: break after controls and LF.
      case BreakProperty::CONTROL:
      case BreakProperty::LF:
        characters.push_back( character );
        character = code_point;
        break;
      case BreakProperty::L:
        switch( property ) {
          // Rule GB6: do not break Hangul syllable sequences.
          case BreakProperty::L:
          case BreakProperty::V:
          case BreakProperty::LV:
          case BreakProperty::LVT:
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            break;
          default:
            characters.push_back( character );
            character = code_point;
        }
        break;
      case BreakProperty::LV:
      case BreakProperty::V:
        switch( property ) {
          // Rule GB7: do not break Hangul syllable sequences.
          case BreakProperty::V:
          case BreakProperty::T:
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            break;
          default:
            characters.push_back( character );
            character = code_point;
        }
        break;
      case BreakProperty::LVT:
      case BreakProperty::T:
        switch( property ) {
          // Rule GB8: do not break Hangul syllable sequences.
          case BreakProperty::T:
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            break;
          default:
            characters.push_back( character );
            character = code_point;
        }
        break;
      case BreakProperty::PREPEND:
        switch( property ) {
          // Rules GB5: break before controls.
          case BreakProperty::CONTROL:
          case BreakProperty::CR:
          case BreakProperty::LF:
            characters.push_back( character );
            character = code_point;
            break;
          // Rule GB9b: do not break after prepend characters.
          default:
            character.append( code_point );
        }
        break;
      case BreakProperty::EXTEND:
        switch( property ) {
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
            character.append( code_point );
            break;
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            within_emoji_modifier = false;
            break;
          default:
            characters.push_back( character );
            character = code_point;
            within_emoji_modifier = false;
        }
        break;
      case BreakProperty::ZWJ:
        switch( property ) {
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            within_emoji_modifier = false;
            break;
          // Rule GB11: do not break within emoji modifier sequences of emoji
          // zwj sequences.
          case BreakProperty::EXTPICT:
            if ( within_emoji_modifier ) {
              character.append( code_point );
              within_emoji_modifier = false;
            } else {
              characters.push_back( character );
              character = code_point;
            }
            break;
          default:
            characters.push_back( character );
            character = code_point;
            within_emoji_modifier = false;
        }
        break;
      case BreakProperty::EXTPICT:
        switch( property ) {
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            break;
          // Rule GB11: do not break within emoji modifier sequences of emoji
          // zwj sequences.
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
            character.append( code_point );
            within_emoji_modifier = true;
            break;
          default:
            characters.push_back( character );
            character = code_point;
        }
        break;
      case BreakProperty::REGIONAL_INDICATOR:
        switch( property ) {
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            is_regional_indicator_nb_odd = false;
            break;
          // Rules GB12 and GB13: do not break within emoji flag sequences. That
          // is, do not break between regional indicator (RI) symbols if there
          // is an odd number of RI characters before the break point.
          case BreakProperty::REGIONAL_INDICATOR:
            is_regional_indicator_nb_odd = !is_regional_indicator_nb_odd;
            if ( is_regional_indicator_nb_odd ) {
              character.append( code_point );
            } else {
              characters.push_back( character );
              character = code_point;
            }
            break;
          default:
            characters.push_back( character );
            character = code_point;
            is_regional_indicator_nb_odd = false;
        }
        break;
      default:
        switch( property ) {
          // Rule GB9: do not break before extending characters or when using a
          // zero-width joiner (ZWJ).
          case BreakProperty::EXTEND:
          case BreakProperty::ZWJ:
          // Rule GB9a: do not break before spacing marks.
          case BreakProperty::SPACINGMARK:
            character.append( code_point );
            break;
          // Rules GB5: break before controls.
          // Rules GB999.
          default:
            characters.push_back( character );
            character = code_point;
        }
    }
  }

  characters.push_back( character );
  return characters;
}

} // unnamed namespace

void Word::BreakIntoCharacters() {
  const CodePointSequence &code_points = BreakIntoCodePoints( text_ );

  characters_ = CharacterRepository::Instance().GetCharacters(
    BreakCodePointsIntoCharacters( code_points ) );
}


void Word::ComputeBytesPresent() {
  for ( const auto &character : characters_ ) {
    for ( uint8_t byte : character->Base() ) {
      bytes_present_.set( byte );
    }
  }
}


Word::Word( const std::string &text )
  : text_( text ) {
  BreakIntoCharacters();
  ComputeBytesPresent();
}

} // namespace YouCompleteMe

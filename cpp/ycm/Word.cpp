// Copyright (C) 2023 ycmd contributors
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

#include "Repository.h"
#include "CodePoint.h"
#include "Word.h"

#include <string>

namespace YouCompleteMe {

namespace {

struct GraphemeBreakAllowedResult {
  bool break_allowed;
  bool within_emoji_modifier;
  bool is_regional_indicator_nb_odd;
};

struct IndicConjunctBreakAllowedResult {
  bool break_allowed;
  bool within_indic_conjunct_modifier;
  bool seen_linker;
};

IndicConjunctBreakAllowedResult IndicConjunctBreakAllowed( IndicBreakProperty previous_indic_property, IndicBreakProperty indic_property, bool within_indic_conjunct_modifier, bool seen_linker ) {
  switch( previous_indic_property ) {
    case IndicBreakProperty::CONSONANT:
      switch( indic_property ) {
        case IndicBreakProperty::EXTEND:
        case IndicBreakProperty::LINKER:
          return { false, true, false };
        default:
          return { true, false, false };
      }
    case IndicBreakProperty::EXTEND:
      switch( indic_property ) {
        case IndicBreakProperty::EXTEND:
        case IndicBreakProperty::LINKER:
          return { !within_indic_conjunct_modifier, within_indic_conjunct_modifier, seen_linker };
        case IndicBreakProperty::CONSONANT:
          return { !seen_linker, false, false };
        default:
          return { true, false, false };
      }
    case IndicBreakProperty::LINKER:
      switch( indic_property ) {
        case IndicBreakProperty::EXTEND:
        case IndicBreakProperty::LINKER:
          return { !within_indic_conjunct_modifier, within_indic_conjunct_modifier, within_indic_conjunct_modifier };
        case IndicBreakProperty::CONSONANT:
          return { !within_indic_conjunct_modifier, false, within_indic_conjunct_modifier };
        default:
          return { true, false, true };
      }
    default:
      return { true, false, false };
  }
}

GraphemeBreakAllowedResult GraphemeBreakAllowed( BreakProperty previous_property, BreakProperty property, bool within_emoji_modifier, bool is_regional_indicator_nb_odd ) {
  // Rules GB1 and GB2 (break at the start and at the end of the text) are
  // automatically satisfied.
  switch( previous_property ) {
    case BreakProperty::CR:
      switch( property ) {
        // Rule GB3: do not break between a CR and LF.
        case BreakProperty::LF:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB4: otherwise, break after CR.
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    // Rule GB4: break after controls and LF.
    case BreakProperty::CONTROL:
    case BreakProperty::LF:
      return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
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
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
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
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
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
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case BreakProperty::PREPEND:
      switch( property ) {
        // Rules GB5: break before controls.
        case BreakProperty::CONTROL:
        case BreakProperty::CR:
        case BreakProperty::LF:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB9b: do not break after prepend characters.
        default:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case BreakProperty::EXTEND:
      switch( property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case BreakProperty::EXTEND:
        case BreakProperty::ZWJ:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB9a: do not break before spacing marks.
        case BreakProperty::SPACINGMARK:
          return { false, false, is_regional_indicator_nb_odd };
        default:
          return { true, false, is_regional_indicator_nb_odd };
      }
    case BreakProperty::ZWJ:
      switch( property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case BreakProperty::EXTEND:
        case BreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case BreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, false };
        // Rule GB11: do not break within emoji modifier sequences of emoji
        // zwj sequences.
        case BreakProperty::EXTPICT:
          return { !within_emoji_modifier, false, is_regional_indicator_nb_odd };
        default:
          return { true, false, is_regional_indicator_nb_odd };
      }
    case BreakProperty::EXTPICT:
      switch( property ) {
        // Rule GB9a: do not break before spacing marks.
        case BreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB11: do not break within emoji modifier sequences of emoji
        // zwj sequences.
        case BreakProperty::EXTEND:
        case BreakProperty::ZWJ:
          return { false, true, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case BreakProperty::REGIONAL_INDICATOR:
      switch( property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case BreakProperty::EXTEND:
        case BreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case BreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, false };
        // Rules GB12 and GB13: do not break within emoji flag sequences. That
        // is, do not break between regional indicator (RI) symbols if there
        // is an odd number of RI characters before the break point.
        case BreakProperty::REGIONAL_INDICATOR:
          return { is_regional_indicator_nb_odd, within_emoji_modifier, !is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, false };
      }
    default:
      switch( property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case BreakProperty::EXTEND:
        case BreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case BreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rules GB5: break before controls.
        // Rules GB999.
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
  }
}

// Break a sequence of code points into characters (grapheme clusters) according
// to the rules in
// https://www.unicode.org/reports/tr29#Grapheme_Cluster_Boundary_Rules
std::vector< std::string > BreakCodePointsIntoCharacters(
  const CodePointSequence &code_points ) {

  std::vector< std::string > characters;

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
  bool within_indic_conjunct_modifier = false;
  bool seen_linker = false;

  for ( ; code_point_pos != code_points.end() ; ++previous_code_point_pos,
                                                ++code_point_pos ) {
    auto previous_property = ( *previous_code_point_pos )->GetBreakProperty();
    auto previous_indic_property = ( *previous_code_point_pos )->GetIndicBreakProperty();
    const auto &code_point = ( *code_point_pos )->Normal();
    auto property = ( *code_point_pos )->GetBreakProperty();
    auto indic_property = ( *code_point_pos )->GetIndicBreakProperty();

    auto [ grapheme_break_allowed, new_within_emoji, new_odd_regional_indicator ] = GraphemeBreakAllowed(previous_property, property, within_emoji_modifier, is_regional_indicator_nb_odd);
    within_emoji_modifier = new_within_emoji;
    is_regional_indicator_nb_odd = new_odd_regional_indicator;

    auto [ indic_conjunct_break_allowed, new_within_indic, new_seen_linker ] = IndicConjunctBreakAllowed( previous_indic_property, indic_property, within_indic_conjunct_modifier, seen_linker );
    within_indic_conjunct_modifier = new_within_indic;
    seen_linker = new_seen_linker;

    if ( grapheme_break_allowed && indic_conjunct_break_allowed ) {
      characters.push_back( character );
      character = code_point;
    } else {
      character.append( code_point );
    }

  }

  characters.push_back( character );
  return characters;
}

} // unnamed namespace

void Word::BreakIntoCharacters() {
  const CodePointSequence &code_points = BreakIntoCodePoints( text_ );

  characters_ = Repository< Character >::Instance().GetElements(
    BreakCodePointsIntoCharacters( code_points ) );
}


void Word::ComputeBytesPresent() {
  for ( const auto &character : characters_ ) {
    for ( auto byte : character->Base() ) {
      bytes_present_.set( static_cast< uint8_t >( byte ) );
    }
  }
}


Word::Word( std::string&& text )
  : text_( std::move( text ) ) {
  BreakIntoCharacters();
  ComputeBytesPresent();
}

} // namespace YouCompleteMe

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

// Implements GB9c grapheme break rule, introduced by Unicode 15.1.
IndicConjunctBreakAllowedResult IndicConjunctBreakAllowed(
	IndicConjunctBreakProperty previous_indic_conjunct_break_property,
	IndicConjunctBreakProperty indic_conjunct_break_property,
	bool within_indic_conjunct_modifier,
	bool seen_linker ) {
  switch( previous_indic_conjunct_break_property ) {
    case IndicConjunctBreakProperty::CONSONANT:
      switch( indic_conjunct_break_property ) {
        // Start of the sequence - do not break.
        case IndicConjunctBreakProperty::EXTEND:
        case IndicConjunctBreakProperty::LINKER:
          return { false, true, false };
        // Either two consecutive consonants or a consonant followed by
        // non-indic codepoint - allow break.
        default:
          return { true, false, false };
      }
    case IndicConjunctBreakProperty::EXTEND:
      switch( indic_conjunct_break_property ) {
        // Either we are continuing an unbreakable sequence, or we can break.
        // Indicated by previous value of within_indic_conjunct_modifier.
        case IndicConjunctBreakProperty::EXTEND:
        case IndicConjunctBreakProperty::LINKER:
          return { !within_indic_conjunct_modifier,
                   within_indic_conjunct_modifier,
                   seen_linker };
        // If we have seen LINKER in the sequence so far, this consonant
        // belongs to the sequence. This is the iffy part, but conformance
        // tests are passing.
        case IndicConjunctBreakProperty::CONSONANT:
          return { !seen_linker, false, false };
        // Definitely break between EXTEND and non-indic codepoint.
        default:
          return { true, false, false };
      }
    case IndicConjunctBreakProperty::LINKER:
      switch( indic_conjunct_break_property ) {
        // Either we are continuing an unbreakable sequence, or we can break.
        // Indicated by previous value of within_indic_conjunct_modifier.
        // If we are in the unbreakable sequence, record that we have seen a
        // linker.
        case IndicConjunctBreakProperty::EXTEND:
        case IndicConjunctBreakProperty::LINKER:
          return { !within_indic_conjunct_modifier,
                   within_indic_conjunct_modifier,
                   within_indic_conjunct_modifier };
        // A LINKER followed by a CONSONANT is the proper way to end a
        // sequence, assuming it has even started.
        case IndicConjunctBreakProperty::CONSONANT:
          return { !within_indic_conjunct_modifier, false, false };
        // Definitely break between EXTEND and non-indic codepoint.
        default:
          return { true, false, false };
      }
    // Definitely break between EXTEND and non-indic codepoint.
    default:
      return { true, false, false };
  }
}

GraphemeBreakAllowedResult GraphemeBreakAllowed(
        GraphemeBreakProperty previous_grapheme_break_property,
        GraphemeBreakProperty grapheme_break_property,
        bool within_emoji_modifier,
        bool is_regional_indicator_nb_odd ) {
  // Rules GB1 and GB2 (break at the start and at the end of the text) are
  // automatically satisfied.
  switch( previous_grapheme_break_property ) {
    case GraphemeBreakProperty::CR:
      switch( grapheme_break_property ) {
        // Rule GB3: do not break between a CR and LF.
        case GraphemeBreakProperty::LF:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB4: otherwise, break after CR.
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    // Rule GB4: break after controls and LF.
    case GraphemeBreakProperty::CONTROL:
    case GraphemeBreakProperty::LF:
      return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
    case GraphemeBreakProperty::L:
      switch( grapheme_break_property ) {
        // Rule GB6: do not break Hangul syllable sequences.
        case GraphemeBreakProperty::L:
        case GraphemeBreakProperty::V:
        case GraphemeBreakProperty::LV:
        case GraphemeBreakProperty::LVT:
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::LV:
    case GraphemeBreakProperty::V:
      switch( grapheme_break_property ) {
        // Rule GB7: do not break Hangul syllable sequences.
        case GraphemeBreakProperty::V:
        case GraphemeBreakProperty::T:
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::LVT:
    case GraphemeBreakProperty::T:
      switch( grapheme_break_property ) {
        // Rule GB8: do not break Hangul syllable sequences.
        case GraphemeBreakProperty::T:
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::PREPEND:
      switch( grapheme_break_property ) {
        // Rules GB5: break before controls.
        case GraphemeBreakProperty::CONTROL:
        case GraphemeBreakProperty::CR:
        case GraphemeBreakProperty::LF:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB9b: do not break after prepend characters.
        default:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::EXTEND:
      switch( grapheme_break_property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, false, is_regional_indicator_nb_odd };
        default:
          return { true, false, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::ZWJ:
      switch( grapheme_break_property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, false };
        // Rule GB11: do not break within emoji modifier sequences of emoji
        // zwj sequences.
        case GraphemeBreakProperty::EXTPICT:
          return { !within_emoji_modifier, false, is_regional_indicator_nb_odd };
        default:
          return { true, false, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::EXTPICT:
      switch( grapheme_break_property ) {
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, is_regional_indicator_nb_odd };
        // Rule GB11: do not break within emoji modifier sequences of emoji
        // zwj sequences.
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
          return { false, true, is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, is_regional_indicator_nb_odd };
      }
    case GraphemeBreakProperty::REGIONAL_INDICATOR:
      switch( grapheme_break_property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
          return { false, within_emoji_modifier, false };
        // Rules GB12 and GB13: do not break within emoji flag sequences. That
        // is, do not break between regional indicator (RI) symbols if there
        // is an odd number of RI characters before the break point.
        case GraphemeBreakProperty::REGIONAL_INDICATOR:
          return { is_regional_indicator_nb_odd,
                   within_emoji_modifier,
                   !is_regional_indicator_nb_odd };
        default:
          return { true, within_emoji_modifier, false };
      }
    default:
      switch( grapheme_break_property ) {
        // Rule GB9: do not break before extending characters or when using a
        // zero-width joiner (ZWJ).
        case GraphemeBreakProperty::EXTEND:
        case GraphemeBreakProperty::ZWJ:
        // Rule GB9a: do not break before spacing marks.
        case GraphemeBreakProperty::SPACINGMARK:
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
    auto previous_grapheme_break_property =
            ( *previous_code_point_pos )->GetGraphemeBreakProperty();
    auto previous_indic_property =
            ( *previous_code_point_pos )->GetIndicConjunctBreakProperty();
    const auto &code_point = ( *code_point_pos )->Normal();
    auto grapheme_break_property =
	    ( *code_point_pos )->GetGraphemeBreakProperty();
    auto indic_conjunct_break_property =
	    ( *code_point_pos )->GetIndicConjunctBreakProperty();

    auto [ grapheme_break_allowed,
           new_within_emoji,
           new_odd_regional_indicator ] = GraphemeBreakAllowed(
                                            previous_grapheme_break_property,
                                            grapheme_break_property,
                                            within_emoji_modifier,
                                            is_regional_indicator_nb_odd );
    within_emoji_modifier = new_within_emoji;
    is_regional_indicator_nb_odd = new_odd_regional_indicator;

    auto [ indic_conjunct_break_allowed,
           new_within_indic,
           new_seen_linker ] = IndicConjunctBreakAllowed(
                                 previous_indic_property,
                                 indic_conjunct_break_property,
                                 within_indic_conjunct_modifier,
                                 seen_linker );
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

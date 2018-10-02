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

#include "IdentifierCompleter.h"

#include "Candidate.h"
#include "IdentifierUtils.h"
#include "Result.h"
#include "Utils.h"

namespace YouCompleteMe {


IdentifierCompleter::IdentifierCompleter(
  const std::vector< std::string > &candidates ) {
  identifier_database_.AddIdentifiers( candidates, "", "" );
}


IdentifierCompleter::IdentifierCompleter(
  const std::vector< std::string > &candidates,
  const std::string &filetype,
  const std::string &filepath ) {
  identifier_database_.AddIdentifiers( candidates, filetype, filepath );
}


void IdentifierCompleter::AddIdentifiersToDatabase(
  const std::vector< std::string > &new_candidates,
  const std::string &filetype,
  const std::string &filepath ) {
  identifier_database_.AddIdentifiers( new_candidates,
                                       filetype,
                                       filepath );
}


void IdentifierCompleter::ClearForFileAndAddIdentifiersToDatabase(
  const std::vector< std::string > &new_candidates,
  const std::string &filetype,
  const std::string &filepath ) {
  identifier_database_.ClearCandidatesStoredForFile( filetype, filepath );
  AddIdentifiersToDatabase( new_candidates, filetype, filepath );
}


void IdentifierCompleter::AddIdentifiersToDatabaseFromTagFiles(
  const std::vector< std::string > &absolute_paths_to_tag_files ) {
  for( const std::string & path : absolute_paths_to_tag_files ) {
    identifier_database_.AddIdentifiers(
      ExtractIdentifiersFromTagsFile( path ) );
  }
}


std::vector< std::string > IdentifierCompleter::CandidatesForQuery(
  const std::string &query,
  const size_t max_candidates ) const {
  return CandidatesForQueryAndType( query, "", max_candidates );
}


std::vector< std::string > IdentifierCompleter::CandidatesForQueryAndType(
  const std::string &query,
  const std::string &filetype,
  const size_t max_candidates ) const {

  std::vector< Result > results;
  identifier_database_.ResultsForQueryAndType( query,
                                               filetype,
                                               results,
                                               max_candidates );

  std::vector< std::string > candidates;
  candidates.reserve( results.size() );

  for ( const Result & result : results ) {
    candidates.push_back( result.Text() );
  }

  return candidates;
}


} // namespace YouCompleteMe

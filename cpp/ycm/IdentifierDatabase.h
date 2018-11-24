// Copyright (C) 2013-2018 ycmd contributors
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

#ifndef IDENTIFIERDATABASE_H_ZESX3CVR
#define IDENTIFIERDATABASE_H_ZESX3CVR

#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <unordered_map>
#include <vector>

namespace YouCompleteMe {

class Candidate;
class Result;
class CandidateRepository;


// filepath -> identifiers
using FilepathToIdentifiers = std::map< std::string,
                                        std::vector< std::string > >;

// filetype -> (filepath -> identifiers)
using FiletypeIdentifierMap = std::map< std::string, FilepathToIdentifiers >;


// This class stores the database of identifiers the identifier completer has
// seen. It stores them in a data structure that makes it easy to tell which
// identifier came from which file and what files have which filetypes.
//
// The main point of this class is to isolate the parts of the code that need
// access to this internal data structure so that it's easier to confirm that
// mutexes are used correctly to protect concurrent access.
//
// This class is thread-safe.
class IdentifierDatabase {
public:
  YCM_EXPORT IdentifierDatabase();
  IdentifierDatabase( const IdentifierDatabase& ) = delete;
  IdentifierDatabase& operator=( const IdentifierDatabase& ) = delete;

  void AddIdentifiers( const FiletypeIdentifierMap &filetype_identifier_map );

  void AddIdentifiers(
    const std::vector< std::string > &new_candidates,
    const std::string &filetype,
    const std::string &filepath );

  void ClearCandidatesStoredForFile( const std::string &filetype,
                                     const std::string &filepath );

  void ResultsForQueryAndType( const std::string &query,
                               const std::string &filetype,
                               std::vector< Result > &results,
                               const size_t max_results ) const;

private:
  std::set< const Candidate * > &GetCandidateSet(
    const std::string &filetype,
    const std::string &filepath );

  void AddIdentifiersNoLock(
    const std::vector< std::string > &new_candidates,
    const std::string &filetype,
    const std::string &filepath );


  // filepath -> *( *candidate )
  using FilepathToCandidates =
    std::unordered_map < std::string,
                         std::shared_ptr< std::set< const Candidate * > > >;

  // filetype -> *( filepath -> *( *candidate ) )
  using FiletypeCandidateMap =
    std::unordered_map < std::string, std::shared_ptr< FilepathToCandidates > >;


  CandidateRepository &candidate_repository_;

  FiletypeCandidateMap filetype_candidate_map_;
  mutable std::mutex filetype_candidate_map_mutex_;
};

} // namespace YouCompleteMe


#endif /* end of include guard: IDENTIFIERDATABASE_H_ZESX3CVR */


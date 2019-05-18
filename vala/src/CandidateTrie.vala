// Copyright (C) 2019 Jakub Kaszycki
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

public class Ycmvala.CandidateTrie : Object {
  private const uint CHAR_TO_INDEX[256] = {
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 54, 99,
    44, 45, 46, 47, 48, 49, 50, 51,
    52, 53, 99, 99, 99, 99, 99, 99,
    99, 27, 28, 29, 30, 31, 32, 33,
    34, 35, 36, 37, 38, 39, 40, 41,
    42, 43, 44, 45, 46, 47, 48, 49,
    50, 51, 52, 99, 99, 99, 99, 26,
    99,  0,  1,  2,  3,  4,  5,  6,
     7,  8,  9, 10, 11, 12, 13, 14,
    15, 16, 17, 18, 19, 20, 21, 22,
    23, 24, 25, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99,
    99, 99, 99, 99, 99, 99, 99, 99
  };

  private Node root = new Node();

  public void build( string prefix,
                     GenericArray< Candidate > candidates ) {
    root.build( (char *) prefix, candidates );
  }

  public new void @set( string name,
                        Candidate candidate,
                        bool replace = false ) {
    root.@set( (char *) name, candidate, replace );
  }

  public void set_all( CandidateTrie trie,
                       bool replace = false ) {
    root.set_all( trie.root, replace );
  }

  [Compact]
  private class Node {
    public Candidate? candidate;
    public Node? children[55];

    public Node() {
      this.candidate = null;
      Memory.@set( children, 0, sizeof( Node? ) * 54 );
    }

    public void build( char *prefix,
                       GenericArray< Candidate > candidates ) {
      if ( *prefix == '\0' ) {
        if ( candidate != null )
          candidates.add( (!) candidate );
        for ( uint i = 0; i < 54; i ++ )
          if ( children[ i ] != null )
            ((!) children[ i ]).build( prefix, candidates );
      } else {
        return_if_fail( CHAR_TO_INDEX[ *prefix ] != 99 );
        var i = CHAR_TO_INDEX[ *prefix ];
        if ( children[ i ] != null )
          ((!) children[ i ]).build( prefix + 1, candidates );
      }
    }

    public Node deep_copy() {
      var result = new Node();
      result.candidate = candidate;

      for ( uint i = 0; i < 54; i ++ )
        if ( children[ i ] != null )
          result.children[ i ] = ((!) children[ i ]).deep_copy();

      return result;
    }

    public void @set( char *name,
                      Candidate candidate,
                      bool replace = false ) {
      if ( *name == '\0' ) {
        if ( this.candidate == null || replace )
          this.candidate = candidate;
      } else {
        return_if_fail( CHAR_TO_INDEX[ *name ] != 99 );
        var i = CHAR_TO_INDEX[ *name ];
        if ( children[ i ] == null )
          children[ i ] = new Node();
        ((!) children[ i ]).@set( name + 1, candidate, replace );
      }
    }

    public void set_all( Node foreign,
                         bool replace = false ) {
      if ( foreign.candidate != null && ( candidate == null || replace ) )
        candidate = foreign.candidate;

      for ( uint i = 0; i < 54; i ++ ) {
        switch ( ( children[ i ] != null ? 1 : 0 )
                 | ( foreign.children[ i ] != null ? 2 : 0 ) ) {
          case 0:
            // Obviously
            break;
          case 1:
            // Also nothing to do.
            break;
          case 2:
            // The merged in trie has this node but this one does not
            // No need to merge, just copy
            children[ i ] = ((!) foreign.children[ i ]).deep_copy();
            break;
          case 3:
            // Now this is the actual merge

            unowned Node my = (!) children[ i ];
            unowned Node your = (!) foreign.children[ i ];

            my.set_all( your, replace );
            break;
        }
      }
    }
  }
}

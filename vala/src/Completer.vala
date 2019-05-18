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

public class Ycmvala.Completer : Object {
  private HashTable< string, TranslationUnit > translation_unit_store
    = new HashTable< string, TranslationUnit >( str_hash,
                                              str_equal );

  public Completer() {
    Object();
  }

  public void delete_translation_unit( string filename ) {
    var tu = get_cached_translation_unit( filename );

    if ( tu != null )
      ((!) tu).unregister( translation_unit_store );
  }

  public TranslationUnit? get_cached_translation_unit( string filename ) {
    return translation_unit_store[ filename ];
  }

  public TranslationUnit get_translation_unit( string filename,
                                               HashTable< string, Bytes > unsaved_files,
                                               string[] flags,
                                               out bool created ) throws CompleterError {
    TranslationUnit tu;

    if ( created = !translation_unit_store.lookup_extended( filename, null, out tu ) ) {
      tu = new TranslationUnit( filename, new Flags( flags ), unsaved_files );
      tu.register( translation_unit_store );
    }

    return (owned) tu;
  }
}

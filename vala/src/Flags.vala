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

public class Ycmvala.Flags : Object {
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? defines = null;
  private bool disable_assert = false;
  private bool disable_since_check = false;
  private bool disable_warnings = false;
  private bool enable_deprecated = false;
  private bool enable_experimental = false;
  private bool enable_experimental_non_null = false;
  private bool fatal_warnings = false;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? fast_vapis = null;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? gir_directories = null;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? gresources = null;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? gresources_directories = null;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? metadata_directories = null;
  private bool nostdpkg = false;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? packages = null;
  private string? pkg_config_command = null;
  private string? profile = null;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? sources_raw = null;
  private string? target_glib = null;
  [CCode( array_length = false,
          array_null_terminated = true )]
  private string[]? vapi_directories = null;

  public Flags( string[] flags ) throws CompleterError {
    Object();

    var optctx = new OptionContext( null );
    optctx.set_help_enabled( false );
    optctx.set_strict_posix( false );

    {
      var options = new OptionEntry[] {
        option_ignored( "abi-stability" ),
        option_ignored( "api-version" ),
        option_ignored( "basedir", 'b', 1 ),
        option_ignored( "cc", 0, 1 ),
        option_ignored( "ccode", 'C' ),
        option_ignored( "color", 0, 2 ),
        option_ignored( "compile", 'c' ),
        option_string_array( "define", 'D', &defines ),
        option_ignored( "deps", 0, 1 ),
        option_ignored( "debug", 'g' ),
        option_ignored( "directory", 'd', 1 ),
        option_boolean( "disable-assert", &disable_assert ),
        option_boolean( "disable-since-check", &disable_since_check ),
        option_ignored( "disable-version-header" ),
        option_boolean( "disable-warnings", &disable_warnings ),
        option_ignored( "dump-tree", 0, 1 ),
        option_ignored( "enable-checking" ),
        option_boolean( "enable-deprecated", &enable_deprecated ),
        option_boolean( "enable-experimental", &enable_experimental ),
        option_boolean( "enable-experimental-non-null", &enable_experimental_non_null ),
        option_ignored( "enable-gobject-tracing" ),
        option_ignored( "enable-mem-profiler" ),
        option_ignored( "enable-version-header" ),
        option_ignored( "fast-vapi", 0, 1 ),
        option_boolean( "fatal-warnings", &fatal_warnings ),
        option_ignored( "gir", 0, 1 ),
        option_filename_array( "girdir", &gir_directories ),
        option_filename_array( "gresources", &gresources ),
        option_filename_array( "gresourcesdir", &gresources_directories ),
        option_ignored( "header", 0, 1 ),
        option_ignored( "help", 'h' ),
        option_ignored( "help-all", '?' ),
        option_ignored( "hide-internal" ),
        option_ignored( "includedir", 0, 1 ),
        option_ignored( "internal-header", 0, 1 ),
        option_ignored( "internal-vapi", 0, 1 ),
        option_ignored( "library", 0, 1 ),
        option_ignored( "main", 0, 1 ),
        option_filename_array( "metadatadir", &metadata_directories ),
        option_ignored( "no-color" ),
        option_boolean( "nostdpkg", &nostdpkg ),
        option_ignored( "output", 0, 1 ),
        option_string_array( "pkg", 0, &packages ),
        option_string( "pkg-config", &pkg_config_command ),
        option_string( "profile", &profile ),
        option_ignored( "quiet", 'q' ),
        option_ignored( "run-args", 0, 1 ),
        option_ignored( "save-temps" ),
        option_ignored( "shared-library", 0, 1 ),
        option_ignored( "symbols", 0, 1 ),
        option_string( "target-glib", &target_glib ),
        option_ignored( "thread" ),
        option_filename_array( "use-fast-vapi", &fast_vapis ),
        option_ignored( "use-header" ),
        option_ignored( "vapi", 0, 1 ),
        option_ignored( "vapi-comments" ),
        option_filename_array( "vapidir", &vapi_directories ),
        option_ignored( "verbose" ),
        option_ignored( "version" ),
        option_ignored( "Xcc", 0, 1 ),
        option_filename_array( OPTION_REMAINING, &sources_raw ),
        OptionEntry()
      };
      optctx.add_main_entries( options, null );
    }

    string[] args;

    if ( flags.length == 0 )
      args = new string[] { "valac", (string) null };
    else if ( flags[0][0] == '-' ) {
      args = new string[flags.length + 2];
      args[0] = "valac";
      for ( uint i = 0; i < flags.length; i ++ )
        args[i + 1] = flags[i];
      args[flags.length + 1] = (string) null;
    } else {
      args = new string[flags.length + 1];
      for ( uint i = 0; i < flags.length; i ++ )
        args[i] = flags[i];
      args[flags.length] = (string) null;
    }

    try {
      if ( !optctx.parse_strv( ref args ) )
        throw new CompleterError.INVALID_FLAGS(
          "Invalid flags"
        );
    } catch ( OptionError error ) {
      throw new CompleterError.INVALID_FLAGS(
        "Invalid flags: %s", error.message
      );
    }
  }

  private void add_pkg( Vala.CodeContext code_context,
                        string pkg ) throws CompleterError {
    if ( !code_context.add_external_package( pkg ) )
      throw new CompleterError.PACKAGE_LOAD_FAILED(
        "Could not load the package %s, see the diagnostics for more information", pkg
      );
  }

  internal Vala.CodeContext create_code_context( TranslationUnit tu ) throws CompleterError {
    var code_context = new Vala.CodeContext();

    var report = new TranslationUnit.Report( tu );
    code_context.report = report;
    report.enable_warnings = !disable_warnings;
    report.set_verbose_errors( true );

    code_context.abi_stability = false;
    code_context.assert = !disable_assert;
    code_context.basedir = "/nonexistent";
    code_context.ccode_only = true;
    code_context.checking = false;
    code_context.compile_only = false;
    code_context.deprecated = enable_deprecated;
    code_context.directory = "/nonexistent2";
    code_context.entry_point_name = (string) null;
    code_context.experimental = enable_experimental;
    code_context.experimental_non_null = enable_experimental_non_null;
    code_context.gobject_tracing = false;
    if ( gresources != null )
      code_context.gresources = (!) gresources;
    if ( gresources_directories != null )
      code_context.gresources_directories = (!) gresources_directories;
    code_context.header_filename = null;
    code_context.hide_internal = false;
    code_context.includedir = null;
    code_context.internal_header_filename = null;
    code_context.nostdpkg = nostdpkg;
    code_context.output = (string) null;
    code_context.pkg_config_command = (!) pkg_config_command;

    if ( profile == null || profile == "gobject" )
      code_context.profile = Vala.Profile.GOBJECT;
    else if ( profile == "posix" )
      code_context.profile = Vala.Profile.POSIX;
    else
      throw new CompleterError.UNKNOWN_PROFILE(
        "Unknown profile: %s", (!) profile
      );

    code_context.run_output = false;
    code_context.since_check = !disable_since_check;
    code_context.symbols_filename = null;
    if ( target_glib != null )
      code_context.set_target_glib_version( (!) target_glib );
    code_context.use_header = false;
    if ( vapi_directories != null )
      code_context.vapi_directories = (!) vapi_directories;
    code_context.verbose_mode = false;
    code_context.version_header = false;

    code_context.add_define( "YOUCOMPLETEME" );

    Vala.Symbol ns_symbol;
    switch( code_context.profile ) {
      case Vala.Profile.GOBJECT:
        ns_symbol = new Vala.UnresolvedSymbol( null, "GLib", null );
        code_context.add_define( "GOBJECT" );
        if ( !nostdpkg ) {
          add_pkg( code_context, "glib-2.0" );
          add_pkg( code_context, "gobject-2.0" );
        }
        break;
      case Vala.Profile.POSIX:
        ns_symbol = new Vala.UnresolvedSymbol( null, "Posix", null );
        code_context.add_define( "POSIX" );
        if ( !nostdpkg )
          add_pkg( code_context, "posix" );
        break;
      default:
        return_val_if_reached( null );
    }

    if ( defines != null )
      foreach ( var define in defines )
        code_context.add_define( define );

    if ( packages != null )
      foreach ( var package in packages )
        add_pkg( code_context, package );

    if ( fast_vapis != null )
      foreach ( var fv in fast_vapis )
        code_context.add_source_file( new Vala.SourceFile( code_context,
                                                           Vala.SourceFileType.FAST,
                                                           fv,
                                                           null,
                                                           false ) );

    if ( sources_raw != null )
      foreach ( var src in sources_raw )
        code_context.add_source_filename( src, true, true );
    else {
      // Heuristic: load all .gs, .vala and .vapi files from current directory
      // Also load current file if not already loaded

      try {
        var dir_path = Path.get_dirname( tu.filename );
        var dir = Dir.open( dir_path );
        var bname = Path.get_basename( tu.filename );

        string? itr;
        while ( ( itr = dir.read_name() ) != null ) {
          if ( ((!) itr).has_suffix( ".gs" ) || ((!) itr).has_suffix( ".vala" ) )
            if ( !code_context.add_source_filename( Path.build_filename( dir_path, (!) itr ), true, true ) )
              throw new FileError.FAILED( "" );
          else if ( ((!) itr).has_suffix( ".vapi" ) ) {
            var path = Path.build_filename( dir_path, (!) itr );
            if ( !code_context.add_source_filename( path, itr == bname, true ) )
              throw new FileError.FAILED( "" );
          }
        }

        if ( !bname.has_suffix( ".gs" ) && !bname.has_suffix( ".vala" ) && !bname.has_suffix( ".vapi " ) )
          if ( !code_context.add_source_filename( tu.filename, true, true ) )
            throw new FileError.FAILED( "" );
      } catch( FileError error ) {
        // Heuristic failed
        throw new CompleterError.NO_FILES(
          "No source files"
        );
      }
    }

    var using_main_ns = new Vala.UsingDirective( ns_symbol, null );
    code_context.root.add_using_directive( using_main_ns );

    foreach (var file in code_context.get_source_files() )
      file.add_using_directive( using_main_ns );

    return code_context;
  }

  private static OptionEntry option_ignored( string long,
                                             char short = 0,
                                             int has_arg = 0 ) {
    return {
      long,
      short,
      has_arg == 1 ? 0 : ( has_arg == 2 ? OptionFlags.OPTIONAL_ARG : OptionFlags.NO_ARG ),
      OptionArg.CALLBACK,
      (void *) parse_ignored_arg,
      (string) null,
      null
    };
  }

  private static OptionEntry option_boolean( string long,
                                             bool *value ) {
    return {
      long,
      0,
      0,
      OptionArg.NONE,
      value,
      (string) null,
      null
     };
  }

  private static OptionEntry option_filename_array( string long,
                                                    void *value ) {
    return {
      long,
      0,
      0,
      OptionArg.FILENAME_ARRAY,
      value,
      (string) null,
      null
    };
  }

  private static OptionEntry option_string( string long,
                                            void *value ) {
    return {
      long,
      0,
      0,
      OptionArg.STRING,
      value,
      (string) null,
      null
     };
  }

  private static OptionEntry option_string_array( string long,
                                                  char short,
                                                  void *value ) {
    return {
      long,
      short,
      0,
      OptionArg.STRING_ARRAY,
      value,
      (string) null,
      null
    };
  }

  private static bool parse_ignored_arg( string option_name,
                                         string? value,
                                         void *data ) throws OptionError {
    return true;
  }
}

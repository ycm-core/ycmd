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

public class Ycmvala.Diagnostic : Object {
  public bool can_fix { get; construct; }
  public DiagnosticKind kind { get; construct; }
  public string message { get; construct; }
  public Range range { get; construct; }

  public Diagnostic( DiagnosticKind kind,
                     Range range,
                     string message,
                     bool can_fix ) {
    Object( can_fix: can_fix,
            kind: kind,
            message: message,
            range: range );
  }
}

// Package testdata is a test input for gocode completions.
package testdata

import "log"

func LogSomeStuff() {
	log.Print("Line 7: Astrid was born on Jan 30")
	log.Print("Line 8: pɹɐɥ sı ǝpoɔıun")
	log.Print("Line 9: Karl was born on Jan 10")
	log.Printf("log prefix: %s", log.Prefix())
}

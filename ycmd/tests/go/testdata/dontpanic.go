// Binary dontpanic has a syntax error which causes a PANIC in gocode.  We
// don't use this in any test, just the related gocode json output, it just
// lives here to document how to make gocode panic. Don't panic, and always
// bring a towel.
package main

import { // <-- should be (, not {
	"fmt"
	"net/http"
}

func main() {
	http.
}

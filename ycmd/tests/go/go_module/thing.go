package main

import "example.com/owner/module/td"

type thinger interface {
  DoThing()
}

type thing string

func (thing) DoThing() {
  td.Hello()
}

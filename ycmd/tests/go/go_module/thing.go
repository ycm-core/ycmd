package main

type thinger interface {
	DoThing()
}

type thing string

func (thing) DoThing() {}

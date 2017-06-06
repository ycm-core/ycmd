# YCMD iOS Swift Example

This directory contains a basic example of an iOS project running under YCMD.

The example contains a project generated from Xcode, minus any unneeded files (
assets, xcodeproj, etc )

It's a simple iOS app and ViewController.swift depends on AppDelegate.swift.

It should serve as a base case so that we can make sure symbols are correctly
loading for people from the iOS SDK and external files.

These abilities are mostly dependent on a correct Compilation Database.

The Compilation Database is a template which is written in test setup. It must
be in the root directory of the examples. This template was generated from a
build of these files under xcodebuild, with the following manual changes:

- replace the source root with __SRCROOT__
- remove 10.3 version requirement
- strip out flags that pass missing build artifacts

//
//  some_swift.swift
//  Swift Completer
//
//  Created by Jerry Marino on 4/30/16.
//  Copyright © 2016 Jerry Marino. All rights reserved.
//

import Foundation

class MySwift : NSObject {
    func sayHello(toPerson: String, otherPerson: String?){
        print("hello \(toPerson), and \(otherPerson)");
    }
    func someOtherFunc(){
    }

    func anotherFunction(){
         self.someOtherFunc()
    }
}


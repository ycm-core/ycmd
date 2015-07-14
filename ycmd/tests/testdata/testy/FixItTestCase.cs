using Microsoft.CSharp;
using System;
using System.Text;

namespace testy {
    public class FixItTestCase {
        public FixItTestCase() {
            var str = "";
            str.EndsWith("A");
            var i = 5;
            const int j = i + 5;
        }

        public int One() {
            var self = this;
            return self.GetHashCode();
        }

        public int Two() {
            var self = this;
            return self.GetHashCode();
        }
    }
}

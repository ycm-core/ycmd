pub trait Foo {
    fn foo(&self);
    fn bar(&self);
}
fn main() {}

#[cfg(test)]
mod tests {
    use super::Foo;
    use mockall::predicate::*;
    use mockall::*;

    mock! {
        FooStruct {
            fn foo(&self);
            fn bar(&self);
        }
    }
    impl Foo for MockFooStruct {
        fn foo(&self) {
            self.foo()
        }

        fn bar(&self) {
            self.bar()
        }
    }

    #[test]
    fn test_test() {
        let mut mock = MockFooStruct::new();

        mock.
    }
}

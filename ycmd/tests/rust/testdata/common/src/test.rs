/// Be careful when using that function
pub fn create_universe() {}

pub struct Builder {}
impl Builder {
  /// Do not try at home
  pub fn build_rocket(&self) {}
  pub fn build_shuttle(&self) {}
}

fn sig_test() {
    let b = Builder{};
    b.build_rocket();
    sig_test();
}

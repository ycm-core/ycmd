mod test;

use test::*;

struct Earth {}
struct Mars {}
trait Atmosphere {}
impl Atmosphere for Earth {}
impl Atmosphere for Mars {}

fn main() {
    create_universe();
    let builder = Builder {};
    builder.build_
}

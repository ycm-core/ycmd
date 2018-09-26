#include "a.hpp" // ./a.hpp
#include <a.hpp> // system/a.hpp
#include "b.hpp" // quote/b.hpp
#include <b.hpp> // error
#include "c.hpp" // system/c.hpp
#include <c.hpp> // system/c.hpp
// not an #include line

#include "dir with spaces/d.hpp"
#include <system/
#include :"

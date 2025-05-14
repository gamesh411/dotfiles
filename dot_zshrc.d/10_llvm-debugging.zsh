run-unit-test() {
   local filter="*${1:-*}*"
   ninja AllClangUnitTests && ./tools/clang/unittests/AllClangUnitTests --gtest_filter="${filter}"
}

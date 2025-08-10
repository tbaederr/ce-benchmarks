// -std=c++23

constexpr int x = []() {
  for (unsigned I = 0; I != (TUNING * 10); ++I) {
    char *buffer = new char[1024];

    for (unsigned c = 0; c != 1023; ++c)
      buffer[c] = 98 + (c % 26);

    delete[] buffer;
  }
  return 1;
}();

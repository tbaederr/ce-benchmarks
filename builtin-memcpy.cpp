// -std=c++20


#ifndef TUNING
#define TUNING 100
#endif

constexpr int test() {
  char A[TUNING] = {};
  char B[TUNING];

  for (unsigned I = 0; I != TUNING; ++I)
    __builtin_memcpy(B, A, TUNING);

  return 1;
}


static_assert(test() == 1);



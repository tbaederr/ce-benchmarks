// -std=c++26

// FASTER VERSION WITH SIZE_T
#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <memory>
#include <optional>
#include <cstdio>

// Handy modulo operator that wraps around automatically
[[nodiscard]] constexpr auto floor_modulo(auto dividend, auto divisor) {
  return ((dividend % divisor) + divisor) % divisor;
}

// This is probably unnecessary, but the min_int
// utilities exist to make the `Point` type as compact as possible
// so that we only use int16 if that's all we need, for example
template <std::size_t value> auto min_int() {
  if constexpr (value <= std::numeric_limits<std::int8_t>::max()) {
    return std::int8_t{};
  } else if constexpr (value <= std::numeric_limits<std::int16_t>::max()) {
    return std::int16_t{};
  } else if constexpr (value <= std::numeric_limits<std::int32_t>::max()) {
    return std::int32_t{};
  } else {
    return std::int64_t{};
  }
}

template <std::size_t value> using min_int_t = decltype(min_int<value>());

// templated on size mostly to give the compiler extra hints
// about the code, so it knows what it can unroll, etc.
template <std::size_t Width, std::size_t Height>
struct GameBoard {
  // These are the properly sized things necessary to hold coordinates
  // that work with this particular size of board
  using x_index_t = std::int64_t;
  using y_index_t = std::int64_t;

  static constexpr std::size_t width = Width;
  static constexpr std::size_t height = Height;

  std::array<bool, Width * Height> data;

  struct Point {
    x_index_t x;
    y_index_t y;
    [[nodiscard]] [[gnu::always_inline]] constexpr Point operator+(Point rhs) const {
      return Point{static_cast<x_index_t>(x + rhs.x),
                   static_cast<y_index_t>(y + rhs.y)};
    }
  };

  // The 8 relative positions for neighbors for a given point
  constexpr static std::array<Point, 8> neighbors{
      Point{-1, 0}, Point{1, 0},
      Point{-1, -1}, Point{0, -1}, Point{1, -1}, 
      Point{-1, 1}, Point{0, 1},  Point{1, 1}};

  // Takes the input point, wraps it vertically/horizontally and takes
  // the new location and maps that to the linear address of the point
  // in the underlying array
  [[nodiscard]] [[gnu::always_inline]] constexpr static std::size_t index(Point p) {
    return static_cast<std::size_t>(floor_modulo(p.y, height) * width +
                                    floor_modulo(p.x, width));
  }

  [[nodiscard]] [[gnu::always_inline]]  constexpr bool operator[](Point p) const noexcept {
    return data[index(p)];
  }

  [[gnu::always_inline]] constexpr void set(Point p) noexcept { data[index(p)] = true; }

  [[nodiscard]] [[gnu::always_inline]] constexpr std::size_t count_neighbors(Point p) const {
    std::size_t count = 0;
    for (const auto &neighbor : neighbors) {
      if ((*this)[p + neighbor]) { ++count; }
    }
    return count;
  }

  // Pre-compute all of the Point coordinates that exist in this particular
  // gameboard. We use this later to iterate over every location in the
  // gameboard.
  [[nodiscard]] static constexpr auto make_indexes() {
    auto result = std::make_unique<std::array<Point, Width * Height>>();

    std::size_t output_index = 0;

    for (y_index_t y = 0; y < height; ++y) {
      for (x_index_t x = 0; x < width; ++x) {
        (*result)[output_index] = Point{x, y};
        ++output_index;
      }
    }
    return result;
  };

  // https://en.wikipedia.org/wiki/Conway's_Game_of_Life#Examples_of_patterns

  // Add a glider at a given location on the game board
  constexpr void add_glider(Point p) {
    set(p);
    set(p + Point{1, 1});
    set(p + Point{2, 1});
    set(p + Point{0, 2});
    set(p + Point{1, 2});
  }
};

template <typename BoardType>
constexpr void iterate_board(const BoardType &input, BoardType &output,
                             auto &indices) {

  const auto rules = [&](const auto &index) {
    const auto neighbor_count = input.count_neighbors(index);
    const auto is_alive = input[index];

    if (is_alive) {
      if (neighbor_count < 2) {
        return false;
      } else if (neighbor_count <= 3) {
        return true;
      } else {
        return false;
      }
    } else {
      if (neighbor_count == 3) {
        return true;
      } else {
        return false;
      }
    }

    return true;
  };

  std::transform(indices.begin(), indices.end(), output.data.begin(), rules);
}

template <std::size_t Width, std::size_t Height, std::size_t Iterations>
constexpr bool run_board() {
  using board_type = GameBoard<Width, Height>;

  // I would consider putting these on the stack, but the GPU engine
  // requires pointers that it knows how to work with. With AdaptiveCpp
  // it swaps out malloc and owns these pointers in a way that can be used
  // with the GPU automagically

  auto board1 = std::make_unique<board_type>();
  board1->add_glider(typename board_type::Point(1, 3));
  board1->add_glider(typename board_type::Point(10, 1));
  auto board2 = std::make_unique<board_type>();

  const auto indices = board_type::make_indexes();

  {
    for (std::size_t i = 0; i < Iterations; ++i) {
      // just swapping buffers back and forth
      iterate_board(*board1, *board2, *indices);
      std::swap(board1, board2);
    }
  }

    // this exists solely to make sure the compiler doesn't optimize out the
    // actual work
    return (*board1)[typename board_type::Point(0, 0)];
}

consteval int foo() {
  // if (run_board<10, 10, 5'000'000>()) { puts("yup1"); }
  if (run_board<TUNING/5, TUNING/5, TUNING/2>()) { puts("yup1"); }
//   if (run_board<100, 10, 500'000>()) { puts("yup2"); }
  // if (run_board<100, 100, 50'000>()) { puts("yup3"); }
  // if (run_board<100, 1000, 5'000>()) { puts("yup4"); }
  // if (run_board<1000, 1000, 500>()) { puts("yup5"); }
  // if (run_board<10000, 1000, 50>()) { puts("yup6"); }
  // if (run_board<10000, 10000, 5>()) { puts("yup7"); }

  return 1;
}

static_assert(foo() == 1);




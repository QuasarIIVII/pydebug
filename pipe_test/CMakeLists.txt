project(
	A
	LANGUAGES CXX
	)
add_compile_options(--static -O3 --std=c++20 -Wall)
add_executable(a a.cpp)


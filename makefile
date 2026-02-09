.PHONY: all clean run

all:
	g++ -std=c++20 main.cpp game/poker.cpp -o poker

run: all
	./poker

clean:
	rm poker
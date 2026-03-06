.PHONY: all clean run equity equity-run gui

all: poker equity_calc

poker:
	g++ -std=c++20 main.cpp game/poker.cpp -o poker

equity_calc:
	g++ -std=c++20 -O2 tools/equity_calc.cpp game/equity.cpp -o equity_calc

equity: equity_calc

run: poker
	./poker

equity-run: equity_calc
	./equity_calc "AA,KK,QQ,AKs" "JJ,TT,AQs" "" 100000

gui: equity_calc
	python3 gui/equity_gui.py

clean:
	rm -f poker equity_calc
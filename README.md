# Car Park Simulator

A desktop tool for modelling the financial viability of a car park. Built with Python and tkinter.

Built on commision.

## What it does

Simulates daily, weekly, monthly, and yearly revenue and costs based on configurable inputs — spaces, occupancy, vehicle mix, staffing, pricing, and more. Includes ANPR cost modelling, mortgage/purchase finance, indoor vs outdoor splits, commuter vs short-stay breakdowns, and a break-even occupancy calculator.

## Running it

```bash
python main.py
```

Requires Python 3.10+. No external dependencies beyond the standard library.

## Running tests

```bash
pip install pytest
pytest test_simulation.py
```

## Project structure

- `engine.py` — simulation logic, all financial calculations
- `models.py` — dataclasses for config and pricing
- `gui.py` — main window and layout
- `gui_controls.py` — left panel (sliders, inputs)
- `gui_results.py` — right panel (results display)
- `gui_widgets.py` — shared widgets (collapsible sections, sliders)

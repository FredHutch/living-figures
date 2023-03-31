# Widget Store
Collection of useful widgets

## Widgets

The interactive data widgets provided in this repository have been
created using the [widgets library](https://www.github.com/FredHutch/widgets).
The idea behind this approach is that the complete set of instructions
needed to visualize a dataset can be packaged together in a single HTML
file along with the data itself so that it can be viewed in any modern
web browser.
The underlying technology which enables this approach is Pyodide,
as well as the [stlite](https://github.com/whitphx/stlite) implementation
of [Streamlit](https://streamlit.io/).

## Using the Store

All of the widgets provided in this store can be installed with:

```
pip install widget-store
```

Once installed, you can load your data into one of these widgets
and save an interactive HTML file with:

```#!/usr/bin/env python
from living_figures.bio import Volcano
import pandas as pd

# Instantiate the widget
volcano = Volcano()

# Read in your data of interest
df = pd.read_csv("your_data.csv")

# Add it to the widget
volcano.set_value("df", df)

# Save an HTML file
volcano.to_html("my_volcano.html")
```

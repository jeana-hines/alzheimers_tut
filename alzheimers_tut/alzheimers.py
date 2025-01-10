
# Use the Agg backend to ensure that matplotlib can generate the map image without relying on a display, which is not available in a server environment.
import matplotlib
matplotlib.use('Agg')

# Import necessary libraries
from flask import Flask, render_template
import geopandas as gpd # library that extends the capabilities of Pandas to work with geospatial data
import pandas as pd # library for data manipulation and analysis
from io import BytesIO # library to handle binary data, such as image data
from matplotlib.backends.backend_agg import FigureCanvasAgg # library to render Matplotlib figures in the Flask app
from matplotlib.figure import Figure # library to create Matplotlib figures
import base64 # library to encode and decode binary data in base64 format

# CHANGE THE FILE PATHS TO MATCH YOUR LOCAL FILE PATHS
csv_file = r"C:\Users\jeana\programming\alzheimers_tut\Weekly_Counts_of_Deaths_by_State_and_Select_Causes__2014-2019.csv" 
shape_path = r"C:\Users\jeana\programming\alzheimers_tut\shape_files\cb_2023_us_state_500k.shp"

# use pandas to load the data from the CSV file
df = pd.read_csv(csv_file)

# Drop unnecessary columns, by index (axis=1 indicates columns, inplace=True modifies the DataFrame directly)
df.drop(df.columns[list(set(range(2, 30)) - {9})], axis=1, inplace=True) 

# Rename columns for clarity
df.rename(columns={"Jurisdiction of Occurrence": "State", "MMWR Year": "Year", "Alzheimer disease (G30)": "Deaths"}, inplace=True)

# Pivot the DataFrame for better analysis, so that each year is a separate column, with the sum of deaths for each state
df_pivoted = df.pivot_table(index='State', columns='Year', values='Deaths', aggfunc='sum')

# Calculate percentage change, handling zero values
df_pivoted['Percent Change'] = df_pivoted.apply(
    lambda row: 0 if (row[2014] == 0 and row[2019] == 0) else 
               100 if row[2014] == 0 else 
               ((row[2019] - row[2014]) / row[2014]) * 100,
    axis=1
)

# Load the shapefile using geopandas
shape = gpd.read_file(shape_path) 

# Merge the shape dataframe with the data dataframe using the 'NAME' column
merged_df = pd.merge(
    left=shape,
    right=df_pivoted,
    left_on='NAME',
    right_index=True,
    how='left'
)

# Drop rows with missing values (NaN) in 'Percent Change' 
merged_df = merged_df.dropna(subset=['Percent Change'])

states_to_exclude = ['Alaska', 'Hawaii', 'Puerto Rico']  # states to exclude from the map
filtered_df = merged_df[~merged_df['NAME'].isin(states_to_exclude)] 

# Create a Flask app
app = Flask(__name__, template_folder='templates') 

@app.route('/')
def index():
    
    # Create the map figure
    fig = Figure(figsize=(10, 6))  # create a figure with a size of 10x6 inches
    ax = fig.add_subplot(111) # add a subplot to the figure (1 row, 1 column, position 1)
    filtered_df.boundary.plot(ax=ax, color='white', linewidth=0.3) # plot the state boundaries in white with a linewidth of 0.3
    filtered_df.plot(
        column='Percent Change', 
        ax=ax, 
        legend=True, 
        cmap='viridis', 
        legend_kwds={'shrink': 0.6, 'orientation': 'horizontal', 'format': '%.0f%%'} #{:.0f}%
    )# plot the choropleth map with the 'Percent Change' column, using the 'viridis' colormap (cmap), and display the legend
    ax.set_title('Percent Change in Alzheimer\'s Fatalities (2014-2019)', fontsize=18, fontweight="bold")
    # Remove axis labels and spines
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    for edge in ['right', 'bottom', 'top', 'left']:
        ax.spines[edge].set_visible(False)

    # Save the plot to a temporary buffer in PNG format
    fig.canvas = FigureCanvasAgg(fig)
    output = BytesIO() # create a BytesIO buffer to store the image data
    fig.savefig(output, format='png') # save the figure to the buffer in PNG format
    output.seek(0) # move the cursor to the beginning of the buffer
    img_url = base64.b64encode(output.getvalue()).decode('utf-8') # encode the image data in base64 format and convert it to a string
    output.close() # close the buffer to free up memory

    return render_template('index.html', img_url=img_url)

if __name__ == "__main__":
    app.run(debug=True)
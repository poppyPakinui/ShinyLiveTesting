# from shiny.express import input, render, ui

import shinylive

from dataclasses import dataclass
from pathlib import Path
from typing import cast
import re

from shiny import App, Inputs, reactive, render, ui
from shiny.ui import TagList, div, h3, head_content, tags, p, hr, a, input_radio_buttons, input_action_button

# Map
import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import pandas as pd
from branca.element import Figure
from ipywidgets import widgets

from bs4 import BeautifulSoup
import fontawesome as fa

# Read data
import geopandas as gpd

# For RStudio connect
import rsconnect

g_mainData = gpd.read_file("data/WWC_Trees/WCC_Trees.shp")

# Transform the coordinate reference system
g_mainData = g_mainData.to_crs(epsg=4326)
# print(g_mainData)
# Sort, create new columns, and select specific columns
g_mainData = g_mainData.sort_values(by='height', ascending=False)
g_mainData['botanical'] = g_mainData['botanical_'].combine_first(g_mainData['botanica_1'])
g_mainData = g_mainData[['OBJECTID', 'botanical', 'height', 'girth', 'address_fu', 'geometry']]

# Create a new column with HTML text for popups
g_mainData['popupText'] = "<b>" + g_mainData['botanical'].astype(str) + "</b><br>" + \
    "Height: " + g_mainData['height'].astype(str) + "m<br>" + \
    "Girth: " + g_mainData['girth'].astype(str) + "cm<br>" + \
    g_mainData['address_fu'].astype(str)

# print(g_mainData)

tagss = BeautifulSoup('<link rel="stylesheet" href="https://use.typekit.net/fkz2upm.css"/>', 'html.parser')
# print(tagss.prettify())


batch_size = 50 # Default
batch_number = 1 # Default

app_ui = ui.page_fluid(
    head_content(
        tags.meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        tags.style((Path(__file__).parent / "./www/style.css").read_text()),
        tags.style("https://use.typekit.net/fkz2upm.css"),
    ),
    div(
        div(
            div(
                h3("Batch loading data"),
                hr(),
                p(
                    "Trees owned/maintained by Parks, Sport, and Recreation Buisness Unit, Wellington City Council"
                ),
                p("Access the data ", tags.a( "here",
                      href = "https://data-wcc.opendata.arcgis.com/datasets/WCC::wcc-trees/about",
                                            target = "_blank"),),
                TagList(input_radio_buttons("batchSize", "Batch Size", choices={"50": 50, "100": 100, "500": 500, "1000": 1000}, selected="50")),
                div(
                    ui.output_ui(id = "output_text"),
                    style = "margin-bottom: 20px;",
                ),
                TagList(
                    input_action_button(
                        label = "Show less",
                        id = "showLess",
                    ),
                    input_action_button(
                        label = "Show more",
                        id = "showMore",
                    ),
                    input_action_button(
                        label = "Reset",
                        id = "reset",
                    ),
                ),
                
                div(tags.img(src = "https://github.com/epi-interactive/Batch_Loading/blob/main/www/images/Epi_Logo.png?raw=true",
                            id = "epi-logo",
                            alt = "EPI LOGO"),
                    id = "logoContainer"),
                class_="sidebar-content-container",
            ),
            class_="sidebar-container",
        ),
        div(
            ui.output_ui("map"),
            class_="map-container",
        ),
        class_="main-container",
        
    ),
    
)


def server(input, output, session):
    
    vals = reactive.value(50)
    b_size = reactive.value(50)
    
   
    @reactive.effect
    @reactive.event(input.showMore)
    def _():
        new_size = (int(vals.get()) + int(input.batchSize()))
        if(new_size <= len(g_mainData)):
            vals.set(new_size)
   
    @reactive.effect
    @reactive.event(input.showLess)
    def _():
        new_size = (int(vals.get()) - int(input.batchSize()))
        if(new_size >= 0):
            vals.set(new_size)
   

    
    @render.ui
    def output_text():
        global batch_size, g_mainData, batch_number
        return p("Showing 1 - ", vals.get(), " of ", len(g_mainData), " locations, tallest to shortest")
    
    @output
    @render.ui
    def map():
        fig = Figure()
        #Define coordinates of where we want to center our map
        epi_coords = [-41.30951339423008, 174.82131380244542]

        #Create the map
        my_map = folium.Map(location = epi_coords, zoom_start = 13, min_zoom=3, zoom_control=False)
        
        fig.add_child(my_map)
        folium.TileLayer('OpenStreetMap').add_to(my_map)
        my_map.add_child(folium.map.CustomPane('labels').add_to(my_map))

        my_map.get_root().html.add_child(folium.Element("""
            <script>
            function addCustomZoomControl(map) {
                var zoomControl = L.control.zoom({ position: 'topright' });
                map.addControl(zoomControl);
            }
            addCustomZoomControl(this);
            </script>
        """))
        renderBatch(my_map, 1)
        # st_data = st_folium(my_map)
        #Display the map
        # return(st_data)
        return(my_map)
    
    def renderBatch(map, currentBatch):
        
        global batch_size
        
        for i in range(vals.get()):
            
            geo = g_mainData.geometry[i]
            ll = {}
            letters = re.sub("[^0-9, ., -]", " ", str(geo))
            letters = re.sub(r"[()]", "", letters)
            
            sp = letters.split()
            
            ll[1] = sp[0]
            ll[0] = sp[1]
            popup_text = "<div style= 'min-width: 150px;'>"+ g_mainData.popupText[i] + "</div>"
            folium.Marker(
                ll, popup = popup_text
                
            ).add_to(map)
        
       
        return map

    # def clearBatch(map, keep):
    #     for batch in range(keep + 1, maxBatches() + 1):
    #         shapeGroupName = f"shapes{batch}"
    #         map.clearGroup(shapeGroupName)
    #     batchSizes.value = batchSizes.value[:keep]
    #     return map
    
    
    # def getBatchNumber():
    #     return
    
    @reactive.effect
    def _():
        f = input.showMore()
        
        global batch_number, batch_size
        batch_number = batch_number + 1
        
    @reactive.effect
    def _():
        f = input.showLess()
        global batch_number
        if(batch_number >0):
            batch_number = batch_number - 1
    
    
    @reactive.effect
    @reactive.event(input.reset)
    def _():
        f = input.batchSize()
        
        global batch_number, batch_size
        batch_number = 1
        
        ui.update_radio_buttons("batchSize", selected="50")
        batch_size = 50
        b_size.set(50)
        vals.set(50)
        
    @reactive.effect
    def _():
        global batch_size
        f = input.batchSize()
        batch_size = int(f)



app = App(app_ui, server, debug=False)

if __name__ == "app":
    print("RUNNING")
    shinylive.run(ui=app_ui, server=server)
    print("FINSIHED RUNNING")
else:
    print("HI" + __name__)

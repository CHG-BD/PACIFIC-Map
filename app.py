import streamlit as st
import pandas as pd
import folium
import requests
import plotly.express as px
from streamlit_folium import st_folium
from branca.element import Template, MacroElement

# --- 1. SETTINGS & CONFIG ---
st.set_page_config(page_title="Philippines Home Improvement Dashboard", layout="wide")
st.title("🇵🇭 Competitor Store Intelligence")

# --- 2. LOAD STORE DATA ---
@st.cache_data
def load_data():
    df = pd.read_excel("competitor_stores_luzon.xlsx")
    df.columns = df.columns.str.strip()
    return df

df = load_data()

# --- 3. LOAD GEOJSON ---
@st.cache_data
def load_luzon_geojson():
    url = "https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/2023/geojson/regions/lowres/regions.json"
    try:
        r = requests.get(url)
        geojson_data = r.json()
        luzon_keywords = ["ncr", "capital", "cordillera", "ilocos", "cagayan", 
                          "central luzon", "calabarzon", "mimaropa", "bicol", 
                          "region i", "region ii", "region iii", "region iv", "region v"]
        luzon_features = [f for f in geojson_data['features'] if any(kw in f['properties'].get('REGION', '').lower() or kw in f['properties'].get('name', '').lower() for kw in luzon_keywords)]
        geojson_data['features'] = luzon_features
        return geojson_data
    except:
        return None

luzon_geojson = load_luzon_geojson()

# --- 4. GLOBAL SIDEBAR FILTERS ---
st.sidebar.header("Global Filters")

# Island Selection
island_options = ["All Philippines", "Luzon", "Visayas", "Mindanao"]
selected_island = st.sidebar.selectbox("Select Island Area", island_options)

# Filter dataset by Island to determine available Regions
temp_df = df.copy()
if selected_island != "All Philippines":
    temp_df = temp_df[temp_df['island_group'].str.contains(selected_island, case=False, na=False)]

# Dynamic Region Filter (Feature 5)
available_regions = temp_df['Region'].dropna().unique().tolist()
selected_regions = st.sidebar.multiselect("Filter by Region", ["All Regions"] + available_regions, default=["All Regions"])

# Competitor Selection (Feature 6)
st.sidebar.subheader("Select Competitors")
competitors = df['competitor'].dropna().unique().tolist()
selected_competitors = []

# Calculate counts for the sidebar checkboxes based on current Island/Region filters
if "All Regions" not in selected_regions and len(selected_regions) > 0:
    temp_df = temp_df[temp_df['Region'].isin(selected_regions)]
competitor_counts = temp_df['competitor'].value_counts()

for comp in competitors:
    count = competitor_counts.get(comp, 0)
    label = f"{comp} ({count})"
    if st.sidebar.checkbox(label, value=True):
        selected_competitors.append(comp)

# Separate map-only filter
st.sidebar.markdown("---")
st.sidebar.header("Map Settings")
show_visited_only_map = st.sidebar.checkbox("Map: Show Only Visited Stores", value=False)
show_region_boundary = st.sidebar.checkbox("Map: Show Luzon Boundaries", value=False)

# --- 5. FILTER THE DATASET FOR DASHBOARD & MAP ---
# Dashboard Data (Ignores the "Show Only Visited" toggle so survey charts work properly)
dash_df = temp_df[temp_df['competitor'].isin(selected_competitors)]

# Map Data
map_df = dash_df.copy()
if show_visited_only_map:
    map_df = map_df[map_df['visited'] == True]

# Unified Base Colors for Map and Plotly
base_colors = {
    'CitiHardware': 'red',
    'AllHome': 'darkorange', 
    'CW Home Depot': 'blue',
    'DO IT Wilcon': 'gold',
    'Wilcon Depot': 'green' 
}

# --- 6. CREATE TABS ---
tab1, tab2 = st.tabs(["🗺️ Map View", "📊 Dashboard View"])

# ==========================================
# TAB 1: MAP VIEW
# ==========================================
with tab1:
    viewport_settings = {
        "Luzon": {"center": [15.5, 121.0], "zoom": 7},
        "Visayas": {"center": [10.5, 124.0], "zoom": 7},
        "Mindanao": {"center": [8.0, 125.0], "zoom": 7},
        "All Philippines": {"center": [12.8797, 121.7740], "zoom": 6}
    }

    center = viewport_settings[selected_island]["center"]
    zoom = viewport_settings[selected_island]["zoom"]
    m = folium.Map(location=center, zoom_start=zoom, tiles="cartodbpositron")

    if show_region_boundary and luzon_geojson:
        folium.GeoJson(
            luzon_geojson,
            style_function=lambda x: {'color': '#ff0000', 'weight': 3, 'fillOpacity': 0.05},
            name="Luzon Regions"
        ).add_to(m)

    # Map CSS gradients (Only used for the map pins)
    css_color_map = base_colors.copy()
    css_color_map['AllHome'] = 'linear-gradient(135deg, orange 50%, green 50%)'
    css_color_map['Wilcon Depot'] = 'linear-gradient(135deg, green 50%, gold 50%)'

    m.get_root().html.add_child(folium.Element('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css"/>'))

    for idx, row in map_df.iterrows():
        if pd.isna(row['latitude']) or pd.isna(row['longitude']): continue
        comp = row['competitor']
        bg_css = css_color_map.get(comp, 'gray')
        
        inner_icon = '<i class="fa-solid fa-star" style="color: black; font-size: 10px;"></i>' if row.get('visited') == True else '<div style="width: 8px; height: 8px; background: white; border-radius: 50%;"></div>'

        custom_html = f"""<div style="width: 22px; height: 22px; border-radius: 50%; background: {bg_css}; border: 2px solid white; display: flex; align-items: center; justify-content: center; box-shadow: 0px 2px 4px rgba(0,0,0,0.5);">{inner_icon}</div>"""
        
        popup_text = f"<b>Branch:</b> {row.get('Branch Name', 'N/A')}<br><b>Company:</b> {comp}<br><b>Region:</b> {row.get('Region', 'N/A')}<br><b>Visited:</b> {'Yes' if row.get('visited') == True else 'No'}"
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"{comp} - {row.get('Branch Name', 'N/A')}",
            icon=folium.DivIcon(html=custom_html)
        ).add_to(m)

    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="position: absolute; bottom: 30px; left: 30px; background-color: white; border: 2px solid grey; z-index: 9999; font-size: 14px; padding: 10px; border-radius: 8px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);">
        <b style="font-size: 16px;">Map Legend</b><br>
        <div style="margin-top: 8px; line-height: 1.8;">
            <div style="display:inline-block; width:16px; height:16px; background:red; border-radius:50%; border:1px solid #ccc; vertical-align:middle; margin-right:8px;"></div> CitiHardware<br>
            <div style="display:inline-block; width:16px; height:16px; background:linear-gradient(135deg, orange 50%, green 50%); border-radius:50%; border:1px solid #ccc; vertical-align:middle; margin-right:8px;"></div> AllHome<br>
            <div style="display:inline-block; width:16px; height:16px; background:blue; border-radius:50%; border:1px solid #ccc; vertical-align:middle; margin-right:8px;"></div> CW Home Depot<br>
            <div style="display:inline-block; width:16px; height:16px; background:gold; border-radius:50%; border:1px solid #ccc; vertical-align:middle; margin-right:8px;"></div> DO IT Wilcon<br>
            <div style="display:inline-block; width:16px; height:16px; background:linear-gradient(135deg, green 50%, gold 50%); border-radius:50%; border:1px solid #ccc; vertical-align:middle; margin-right:8px;"></div> Wilcon Depot<br>
            <hr style="margin: 8px 0; border: 0; border-top: 1px solid #ddd;">
            <div style="display:flex; align-items:center;">
                <div style="width: 16px; height: 16px; background: white; border-radius: 50%; border: 1px solid grey; display: flex; align-items: center; justify-content: center; margin-right:8px;">
                    <i class="fa-solid fa-star" style="color: black; font-size: 8px;"></i>
                </div> Visited Store
            </div>
        </div>
    </div>
    {% endmacro %}
    """
    macro = MacroElement()
    macro._template = Template(legend_html)
    m.get_root().add_child(macro)

    st.markdown(f"**Showing {len(map_df)} stores** on map.")
    st_folium(m, width=1000, height=600, returned_objects=[])

# ==========================================
# TAB 2: DASHBOARD VIEW
# ==========================================
with tab2:
    if dash_df.empty:
        st.warning("No data available for the selected filters.")
    else:
        # --- Feature 1: Total Stores & Visit KPIs ---
        st.subheader("Survey Overview")
        total_stores = len(dash_df)
        visited_stores = len(dash_df[dash_df['visited'] == True])
        unvisited_stores = total_stores - visited_stores
        visited_pct = (visited_stores / total_stores * 100) if total_stores > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Targeted Stores", total_stores)
        col2.metric("Visited", visited_stores)
        col3.metric("Unvisited", unvisited_stores)
        col4.metric("Survey Completion %", f"{visited_pct:.1f}%")

        st.markdown("---")

        # --- Layout for Charts ---
        chart_col1, chart_col2 = st.columns(2)

        # --- Feature 2: Share of Stores (Donut Chart) ---
        with chart_col1:
            st.subheader("Market Share (Branch Count)")
            donut_data = dash_df['competitor'].value_counts().reset_index()
            donut_data.columns = ['Competitor', 'Store Count']
            
            fig_donut = px.pie(
                donut_data, 
                values='Store Count', 
                names='Competitor', 
                hole=0.4,
                color='Competitor',
                color_discrete_map=base_colors
            )
            st.plotly_chart(fig_donut, use_container_width=True)

        # --- Feature 4: Survey Tracking (Stacked Bar Chart) ---
        with chart_col2:
            st.subheader("Survey Tracking by Competitor")
            survey_data = dash_df.groupby(['competitor', 'visited']).size().reset_index(name='Count')
            survey_data['Status'] = survey_data['visited'].map({True: 'Visited', False: 'Unvisited'})
            
            fig_survey = px.bar(
                survey_data, 
                x='competitor', 
                y='Count', 
                color='Status',
                color_discrete_map={'Visited': '#2e7b32', 'Unvisited': '#e0e0e0'}, # Green for visited, Grey for unvisited
                barmode='stack',
                labels={'competitor': 'Competitor'}
            )
            st.plotly_chart(fig_survey, use_container_width=True)

        st.markdown("---")

        # --- Feature 3: Store Distribution by Region (Grouped Bar Chart) ---
        st.subheader(f"Store Distribution across Regions")
        
        region_data = dash_df.groupby(['Region', 'competitor']).size().reset_index(name='Store Count')
        
        # Sort regions alphabetically for better readability
        region_data = region_data.sort_values('Region')

        fig_region = px.bar(
            region_data, 
            x='Region', 
            y='Store Count', 
            color='competitor', 
            barmode='group',
            color_discrete_map=base_colors,
            labels={'competitor': 'Competitor'}
        )
        
        # Rotate x-axis labels so long region names don't overlap
        fig_region.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig_region, use_container_width=True)
# Toronto Urban Data Pipeline

An automated GIS data pipeline built with ArcPy and Python, processing real City of Toronto Open Data across four workflows: data auditing, spatial analysis, coordinate system management, and automated map production.

Built as a portfolio project targeting GIS Technician and Junior GIS Analyst roles in Ontario.

---

## Project Overview

Municipal GIS datasets arrive in inconsistent formats, wrong projections, and with missing attributes. This pipeline automates the entire preparation and publishing workflow — from raw shapefile to print-ready ward maps — without manual intervention.

**Data processed:**
- 64,659 road segments (Toronto Centreline)
- 25 ward polygons (City of Toronto Ward Boundaries)

**Final output:**
- 25 individual ward PDF maps, each zoomed and labelled automatically
- Ward centroid CSV for web mapping applications
- Fully audited and reprojected GDB in NAD83 CSRS UTM Zone 17N

---

## Scripts

### 01_data_audit.py — Data Audit and Field Cleaning

Loops through all layers in the File Geodatabase, reports coordinate systems, and flags anything not meeting the NAD83 CSRS standard used by Canadian federal agencies. Adds a `STREET_NAME_CLEAN` field and standardizes 64,659 street names from legacy ALL CAPS formatting to Title Case using `CalculateField`.

**Key functions:** `arcpy.ListFeatureClasses`, `arcpy.Describe`, `AddField_management`, `CalculateField_management`

---

### 02_data_analysis.py — Cursor-Based Analysis and Geometry Extraction

Uses `arcpy.da.SearchCursor` to inventory all road types across 64,659 segments, then applies `arcpy.da.UpdateCursor` to assign speed limits based on Ontario road classification rules. Extracts ward polygon centroids using the `SHAPE@XY` geometry token and exports to CSV with Google Maps verification links.

**Key functions:** `arcpy.da.SearchCursor`, `arcpy.da.UpdateCursor`, `SHAPE@XY`, `csv.DictWriter`

---

### 03_reproject_nad83.py — Reprojection to NAD83 CSRS

Detects the current CRS of each layer using `arcpy.Describe`, calculates the correct UTM zone automatically from the dataset's geographic extent, and reprojects to NAD83 CSRS UTM Zone 17N. Applies the `NAD_1983_CSRS_To_WGS_1984_2` datum transformation — omitting this parameter causes a silent ~1.5 metre positional shift in Ontario, which is unacceptable for infrastructure or surveying work.

**Key functions:** `arcpy.Project_management`, `arcpy.SpatialReference`, `geo_transformation`

---

### 04_export_ward_maps.py — Automated Ward Map Production

Opens an ArcGIS Pro project using `arcpy.mp`, controls layer visibility programmatically, and exports 25 individual ward PDFs by looping through ward polygons with a SearchCursor. For each ward, the MapFrame camera is repositioned to the ward extent, a definition query highlights the active ward boundary, and layout text elements are updated automatically before export.

**Key functions:** `arcpy.mp.ArcGISProject`, `MapFrame.camera.setExtent`, `Layout.exportToPDF`, `TextElement`, `definitionQuery`

---

## Skills Demonstrated

| Skill | Where Used |
|---|---|
| `ListFeatureClasses` + `Describe` | CRS audit across all GDB layers |
| `AddField` + `CalculateField` | Street name standardization |
| `arcpy.da.SearchCursor` | Road type inventory, centroid extraction |
| `arcpy.da.UpdateCursor` | Speed limit assignment across 64,659 rows |
| `SHAPE@XY` geometry token | Ward centroid coordinates without extra geoprocessing |
| `arcpy.Project_management` | Datum-aware reprojection to NAD83 CSRS |
| `geo_transformation` parameter | Correct WGS84 → NAD83 CSRS shift for Ontario |
| UTM zone calculation | Automatic zone detection from extent centre longitude |
| `arcpy.mp` mapping module | Layout automation, text element control |
| `MapFrame.camera.setExtent` | Per-ward zoom without manual panning |
| `definitionQuery` | Highlight active ward per PDF export |
| `Layout.exportToPDF` | Batch PDF production from a single layout |

---

## Data Sources

All data is publicly available from the City of Toronto Open Data Portal.

- [Toronto Centreline](https://open.toronto.ca/dataset/toronto-centreline-tcl/) — road network, 64,659 segments
- [City Wards](https://open.toronto.ca/dataset/city-wards/) — 25-ward model, ward boundaries

Both datasets were downloaded in WGS84 (EPSG:4326) and reprojected to NAD83 CSRS UTM Zone 17N for analysis.

---

## Setup

**Requirements:**
- ArcGIS Pro 3.x with ArcPy
- Python 3.x (included with ArcGIS Pro)
- City of Toronto shapefiles imported into a File Geodatabase

**Configuration:**

Update `PROJECT_ROOT` in each script to match your local path:

```python
PROJECT_ROOT = r"C:\your\path\to\Toronto"
```

All other paths are built automatically from this variable.

**Run order:**

```
01_data_audit.py        # audit layers, clean street names
02_data_analysis.py     # assign speed limits, export centroids
03_reproject_nad83.py   # reproject to NAD83 CSRS UTM Zone 17N
04_export_ward_maps.py  # export 25 ward PDFs
```

Each script is independent and can be run individually after setup.

---

## Output

```
Toronto/
    ArcGIS/
        Toronto_Pipeline.gdb        # GDB with all processed layers
    PDF_Maps/
        Toronto_Road_Network.pdf    # full city road map
        Ward_PDFs/
            Ward_01_Etobicoke_North.pdf
            Ward_02_Etobicoke_Centre.pdf
            ... (25 total)
            Ward_25_Scarborough-Rouge_Park.pdf
    ward_centroids.csv              # ward centroids with Google Maps links
```
**Sample output:**[Ward 07 — Humber River-Black Creek](https://github.com/Mi9320/toronto-urban-data-pipeline/blob/main/Ward_07_Humber_River-Black_C.pdf)
---

## Background

**Author:** Ibrahim Mirza  
**Target roles:** GIS Technician, Junior GIS Analyst 

The Environmental Management background provides direct relevance to Conservation Authority and Ministry of Environment GIS roles, where understanding of wetland mapping, species at risk, and environmental impact assessment context is valued alongside technical GIS skills.

---

## Contact

Open to GIS Technician and Junior GIS Analyst opportunities.  
Connect on [LinkedIn](https://www.linkedin.com/in/ibrahim-mirza3/) or reach out via GitHub.

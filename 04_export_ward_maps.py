# =============================================================================
# Toronto Urban Data Pipeline
# Script 04 — Automated Ward Map Export
#
# Author  : Ibrahim Mirza
# Date    : 2026
#
# Description:
#   Uses the arcpy mapping module (arcpy.mp) to automate production of
#   25 individual ward maps from a single ArcGIS Pro layout. Each PDF
#   is zoomed to the ward extent, titled, and labelled automatically.
#   Replaces a manual process that would otherwise take several hours.
#
#   Also demonstrates layer visibility control for producing thematic
#   single-layer exports from a multi-layer map.
#
# Data Sources:
#   - City_Wards_NAD83_UTM17N (produced by 03_reproject_nad83.py)
#   - Centreline_NAD83_UTM17N (produced by 03_reproject_nad83.py)
#
# Skills:
#   arcpy.mp.ArcGISProject, Layout.exportToPDF, MapFrame.camera.setExtent,
#   TextElement manipulation, layer visibility, definition queries
# =============================================================================

import arcpy
import arcpy.mp
import os
import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = r"C:\arcgis pro arc py\Toronto"
GDB_PATH     = os.path.join(PROJECT_ROOT, "ArcGIS", "Toronto_Pipeline.gdb")
APRX_PATH    = os.path.join(PROJECT_ROOT, "ArcGIS", "Toronto_Publisher.aprx")
PDF_FOLDER   = os.path.join(PROJECT_ROOT, "PDF_Maps")

# Names must match exactly what is set in the ArcGIS Pro project
MAP_NAME           = "Map"
LAYOUT_NAME        = "Layout"
TITLE_ELEMENT      = "Toronto Ward Map"
WARD_NAME_ELEMENT  = "Ward Name"
ROADS_LAYER_NAME   = "Centreline"
WARDS_LAYER_NAME   = "City Wards"

# Ward fields — confirmed from 02_data_analysis.py output
WARD_NAME_FIELD    = "AREA_NA13"
WARD_NUMBER_FIELD  = "AREA_SH11"


# ---------------------------------------------------------------------------
# Open the project and report its contents
# ---------------------------------------------------------------------------

def inspect_project(aprx_path):
    """
    Opens the .aprx file and prints all maps, layers, layouts, and
    layout elements. Run this first to confirm element names match
    the configuration variables above before exporting.
    """
    print("--- Project Inspection ---\n")

    if not os.path.exists(aprx_path):
        print(f"    Project not found: {aprx_path}")
        print("    Update APRX_PATH in the configuration section.")
        return None

    aprx = arcpy.mp.ArcGISProject(aprx_path)
    print(f"    Opened: {aprx_path}\n")

    for m in aprx.listMaps():
        print(f"    Map: '{m.name}'")
        for lyr in m.listLayers():
            state = "on " if lyr.visible else "off"
            print(f"      [{state}] {lyr.name}")
        print()

    for layout in aprx.listLayouts():
        print(f"    Layout: '{layout.name}' ({layout.pageWidth}\" x {layout.pageHeight}\")")
        for elem in layout.listElements():
            print(f"      {elem.type:<30} '{elem.name}'")
            if elem.type == "TEXT_ELEMENT":
                print(f"        text: '{elem.text}'")
        print()

    return aprx


# ---------------------------------------------------------------------------
# Layer visibility export — one PDF per layer
# ---------------------------------------------------------------------------

def export_by_layer(aprx, pdf_folder):
    """
    Turns each target layer on exclusively and exports a PDF.
    Restores original visibility when done.

    Useful for producing thematic maps from a multi-layer project
    without manually toggling layers in the ArcGIS Pro interface.
    """
    print("--- Single-Layer PDF Export ---\n")

    the_map    = aprx.listMaps(MAP_NAME)[0]
    the_layout = aprx.listLayouts(LAYOUT_NAME)[0]
    title_elem = the_layout.listElements("TEXT_ELEMENT", TITLE_ELEMENT)[0]

    all_layers   = the_map.listLayers()
    original_vis = {lyr.name: lyr.visible for lyr in all_layers}

    os.makedirs(pdf_folder, exist_ok=True)

    for target in [ROADS_LAYER_NAME, WARDS_LAYER_NAME]:
        match = the_map.listLayers(target)
        if not match:
            print(f"    Layer '{target}' not found in map. Skipping.")
            continue

        for lyr in all_layers:
            lyr.visible = False
        match[0].visible = True

        title_elem.text = f"Toronto — {target}"

        out_path = os.path.join(pdf_folder, f"{target.replace(' ', '_')}.pdf")
        the_layout.exportToPDF(out_pdf=out_path, resolution=150, image_quality="NORMAL")
        print(f"    Exported: {out_path}")

    for lyr in all_layers:
        lyr.visible = original_vis.get(lyr.name, True)
    title_elem.text = "Toronto Ward Map"


# ---------------------------------------------------------------------------
# Ward-by-ward PDF export
# ---------------------------------------------------------------------------

def export_ward_maps(aprx, pdf_folder):
    """
    Loops through all 25 Toronto wards and exports a separate PDF for each.

    For each ward:
      1. Reads the polygon geometry with SHAPE@ cursor token
      2. Expands the extent by 20% so the ward boundary has breathing room
      3. Sets the MapFrame camera to that extent
      4. Applies a definition query to highlight only the current ward
      5. Updates the title and ward name text elements
      6. Exports to PDF at 200 DPI

    This replaces a manual process of opening the layout, panning to
    each ward, updating the title, and exporting — repeated 25 times.
    """
    print("--- Ward Map Export ---\n")

    the_map    = aprx.listMaps(MAP_NAME)[0]
    the_layout = aprx.listLayouts(LAYOUT_NAME)[0]

    map_frames = the_layout.listElements("MAPFRAME_ELEMENT")
    if not map_frames:
        print("    No MapFrame found in layout.")
        return
    map_frame = map_frames[0]

    title_elems = the_layout.listElements("TEXT_ELEMENT", TITLE_ELEMENT)
    if not title_elems:
        print(f"    Title element '{TITLE_ELEMENT}' not found.")
        return
    title_elem = title_elems[0]

    ward_name_elems = the_layout.listElements("TEXT_ELEMENT", WARD_NAME_ELEMENT)
    ward_name_elem  = ward_name_elems[0] if ward_name_elems else None

    # Find the wards layer for definition query highlighting
    wards_map_layer = None
    for lyr in the_map.listLayers():
        if "City Wards" in lyr.name or "City_Wards" in lyr.name:
            wards_map_layer = lyr
            break

    out_folder = os.path.join(pdf_folder, "Ward_PDFs")
    os.makedirs(out_folder, exist_ok=True)

    wards_path = os.path.join(GDB_PATH, "City_Wards_NAD83_UTM17N")
    if not arcpy.Exists(wards_path):
        print(f"    Wards layer not found: {wards_path}")
        print("    Run 03_reproject_nad83.py first.")
        return

    exported = 0
    errors   = []

    print(f"    {'Ward':<6} {'Name':<35} Status")
    print(f"    {'-'*6} {'-'*35} {'-'*10}")

    with arcpy.da.SearchCursor(wards_path, [WARD_NAME_FIELD, WARD_NUMBER_FIELD, "SHAPE@"]) as cursor:
        for row in cursor:
            ward_name   = row[0] or "Unknown"
            ward_number = row[1] or "00"
            geom        = row[2]

            try:
                ext  = geom.extent
                xbuf = (ext.XMax - ext.XMin) * 0.20
                ybuf = (ext.YMax - ext.YMin) * 0.20

                buffered = arcpy.Extent(
                    ext.XMin - xbuf,
                    ext.YMin - ybuf,
                    ext.XMax + xbuf,
                    ext.YMax + ybuf
                )

                map_frame.camera.setExtent(buffered)

                if wards_map_layer:
                    wards_map_layer.definitionQuery = f"AREA_SH11 = '{ward_number}'"

                title_elem.text = "Toronto Ward Map"

                if ward_name_elem:
                    ward_name_elem.text = f"Ward {ward_number} — {ward_name}"

                safe = f"Ward_{str(ward_number).zfill(2)}_{ward_name[:20]}"
                safe = safe.replace(" ", "_").replace("/", "-").replace(".", "").replace("'", "")

                the_layout.exportToPDF(
                    out_pdf       = os.path.join(out_folder, f"{safe}.pdf"),
                    resolution    = 200,
                    image_quality = "BEST"
                )

                exported += 1
                print(f"    {str(ward_number):<6} {ward_name:<35} OK")

            except Exception as e:
                errors.append(f"Ward {ward_number}: {e}")
                print(f"    {str(ward_number):<6} {ward_name:<35} ERROR")

    # Restore layout and layer state
    title_elem.text = "Toronto Ward Map"
    if ward_name_elem:
        ward_name_elem.text = "Ward Name:"
    if wards_map_layer:
        wards_map_layer.definitionQuery = ""

    print(f"\n    Exported : {exported} / 25")
    if errors:
        print(f"    Errors   : {len(errors)}")
        for e in errors:
            print(f"      {e}")
    print(f"    Folder   : {out_folder}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  Toronto Urban Data Pipeline — 04 Export Ward Maps")
    print(f"  Run at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    os.makedirs(PDF_FOLDER, exist_ok=True)

    aprx = inspect_project(APRX_PATH)

    if aprx is None:
        print("Cannot continue — fix APRX_PATH and rerun.")
    else:
        export_by_layer(aprx, PDF_FOLDER)
        export_ward_maps(aprx, PDF_FOLDER)

        # Uncomment the line below if ArcGIS Pro is NOT open at the same time
        # aprx.save()

    print("\n" + "=" * 60)
    print("  Pipeline complete.")
    print("=" * 60 + "\n")

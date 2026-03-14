# =============================================================================
# Toronto Urban Data Pipeline
# Script 02 — Cursor-Based Data Analysis and Geometry Extraction
#
# Author  : Ibrahim Mirza
# Date    : 2026
#
# Description:
#   Performs row-level data operations on Toronto road and ward datasets
#   using arcpy data access cursors. Assigns speed limits to 64,659 road
#   segments based on road classification, and extracts ward polygon
#   centroids to a CSV for use in web mapping applications.
#
# Data Sources:
#   - Toronto Centreline (City of Toronto Open Data)
#   - City of Toronto Ward Boundaries (City of Toronto Open Data)
#
# Skills:
#   arcpy.da.SearchCursor, arcpy.da.UpdateCursor,
#   SHAPE@XY geometry token, csv.DictWriter
# =============================================================================

import arcpy
import os
import csv
import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = r"C:\arcgis pro arc py\Toronto"
GDB_PATH     = os.path.join(PROJECT_ROOT, "ArcGIS", "Toronto_Pipeline.gdb")
CSV_OUTPUT   = os.path.join(PROJECT_ROOT, "ward_centroids.csv")

ROADS_LAYER       = "Centreline___Version_2___4326"
WARDS_LAYER       = "City_Wards_Data___4326"

TYPE_FIELD        = "FEATURE36"   # road classification field
SPEED_FIELD       = "SPEED_LIMIT_KMH"
WARD_NAME_FIELD   = "AREA_NA13"
WARD_NUMBER_FIELD = "AREA_SH11"


# ---------------------------------------------------------------------------
# Road type inventory using SearchCursor
# ---------------------------------------------------------------------------

def road_type_inventory(gdb_path, roads_layer):
    """
    Reads every road segment and counts occurrences of each road type.

    SearchCursor is used instead of summary statistics because it gives
    full programmatic control over the output — results feed directly
    into the speed limit rules in assign_speed_limits().
    """
    print("--- Road Type Inventory ---\n")

    roads_path = os.path.join(gdb_path, roads_layer)
    counts     = {}

    with arcpy.da.SearchCursor(roads_path, [TYPE_FIELD]) as cursor:
        for row in cursor:
            road_type = row[0]
            if road_type:
                counts[road_type] = counts.get(road_type, 0) + 1

    print(f"    {'Road Type':<40} {'Count':>8}")
    print(f"    {'-'*40} {'-'*8}")

    for rtype, cnt in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {rtype:<40} {cnt:>8,}")

    print(f"    {'-'*40} {'-'*8}")
    print(f"    {'Total':<40} {sum(counts.values()):>8,}\n")

    return counts


# ---------------------------------------------------------------------------
# Assign speed limits using UpdateCursor
# ---------------------------------------------------------------------------

def assign_speed_limits(gdb_path, roads_layer):
    """
    Adds SPEED_LIMIT_KMH and assigns values based on road classification.

    UpdateCursor is the correct tool here — CalculateField cannot apply
    conditional logic across multiple field values without a complex
    expression. The cursor reads TYPE_FIELD and writes SPEED_FIELD
    row by row across all 64,659 segments.

    Speed values follow Ontario Highway Traffic Act classifications
    and City of Toronto posted speed guidelines.
    """
    print("--- Assigning Speed Limits ---\n")

    roads_path = os.path.join(gdb_path, roads_layer)
    fields     = [f.name for f in arcpy.ListFields(roads_path)]

    if SPEED_FIELD not in fields:
        print(f"    Adding field: {SPEED_FIELD}")
        arcpy.management.AddField(
            in_table   = roads_path,
            field_name = SPEED_FIELD,
            field_type = "SHORT",
            field_alias= "Speed Limit (km/h)"
        )

    # Speed rules based on Ontario road classifications
    speed_rules = {
        "Expressway"            : 100,
        "Expressway Ramp"       : 60,
        "Major Arterial"        : 60,
        "Major Arterial Ramp"   : 60,
        "Minor Arterial"        : 50,
        "Collector"             : 50,
        "Collector Ramp"        : 50,
        "Local"                 : 40,
        "Laneway"               : 20,
        "Access Road"           : 30,
        "Busway"                : 90,
        "Major Railway"         : 0,
        "Minor Railway"         : 0,
        "Trail"                 : 0,
        "River"                 : 0,
        "Hydro Line"            : 0,
        "Walkway"               : 0,
        "Ferry Route"           : 0,
        "Creek/Tributary"       : 0,
        "Other"                 : 20,
        "Pending"               : 20,
    }

    default_speed = 40
    updated       = 0
    summary       = {}

    with arcpy.da.UpdateCursor(roads_path, [TYPE_FIELD, SPEED_FIELD]) as cursor:
        for row in cursor:
            road_type = row[0]
            speed     = speed_rules.get(road_type, default_speed) if road_type else default_speed
            row[1]    = speed
            cursor.updateRow(row)
            updated  += 1
            if road_type:
                summary[road_type] = summary.get(road_type, 0) + 1

    print(f"    {updated:,} segments updated.\n")
    print(f"    {'Road Type':<35} {'Count':>8} {'Speed':>8}")
    print(f"    {'-'*35} {'-'*8} {'-'*8}")

    for rtype, cnt in sorted(summary.items(), key=lambda x: x[1], reverse=True):
        spd = speed_rules.get(rtype, default_speed)
        print(f"    {rtype:<35} {cnt:>8,} {str(spd)+' km/h':>8}")


# ---------------------------------------------------------------------------
# Export ward centroids to CSV using SHAPE@XY
# ---------------------------------------------------------------------------

def export_ward_centroids(gdb_path, wards_layer, output_csv):
    """
    Extracts the centroid of each ward polygon and writes to CSV.

    SHAPE@XY returns the (longitude, latitude) of the polygon centroid
    without requiring a separate geoprocessing step. Output includes a
    Google Maps URL for quick visual verification of each coordinate.

    Intended output: coordinates for placement of map markers on the
    City of Toronto public-facing ward portal.
    """
    print("\n--- Exporting Ward Centroids ---\n")

    wards_path = os.path.join(gdb_path, wards_layer)

    if not arcpy.Exists(wards_path):
        print(f"    Layer not found: {wards_layer}")
        return

    cursor_fields = [WARD_NAME_FIELD, WARD_NUMBER_FIELD, "SHAPE@XY"]
    ward_data     = []

    with arcpy.da.SearchCursor(wards_path, cursor_fields) as cursor:
        for row in cursor:
            name      = row[0] or "Unknown"
            number    = row[1] or "N/A"
            lon       = round(row[2][0], 6)
            lat       = round(row[2][1], 6)

            ward_data.append({
                "Ward_Number"    : number,
                "Ward_Name"      : name,
                "Longitude"      : lon,
                "Latitude"       : lat,
                "Google_Maps_URL": f"https://www.google.com/maps?q={lat},{lon}"
            })

            print(f"    Ward {str(number):<4}  {name:<30}  {lat}, {lon}")

    out_dir = os.path.dirname(output_csv)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Ward_Number", "Ward_Name",
                                                "Longitude", "Latitude",
                                                "Google_Maps_URL"])
        writer.writeheader()
        writer.writerows(ward_data)

    print(f"\n    {len(ward_data)} wards written to: {output_csv}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  Toronto Urban Data Pipeline — 02 Data Analysis")
    print("=" * 60)

    arcpy.env.workspace       = GDB_PATH
    arcpy.env.overwriteOutput = True

    road_type_inventory(GDB_PATH, ROADS_LAYER)
    assign_speed_limits(GDB_PATH, ROADS_LAYER)
    export_ward_centroids(GDB_PATH, WARDS_LAYER, CSV_OUTPUT)

    print("\n" + "=" * 60)
    print("  Script complete — ready for 03_reproject_nad83.py")
    print("=" * 60 + "\n")

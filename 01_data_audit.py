# =============================================================================
# Toronto Urban Data Pipeline
# Script 01 — Data Audit and Field Cleaning
#
# Author  : Ibrahim Mirza
# Date    : 2026
#
# Description:
#   Ingests Toronto Open Data shapefiles into a File Geodatabase and performs
#   automated quality checks before any analysis begins. Flags layers that
#   do not meet the NAD83 CSRS standard used by Canadian federal agencies,
#   and standardizes street name formatting across 64,659 road segments.
#
# Data Sources:
#   - Toronto Centreline (City of Toronto Open Data)
#   - City of Toronto Ward Boundaries — 25-Ward Model (City of Toronto Open Data)
#
# Skills:
#   arcpy.ListFeatureClasses, arcpy.Describe, AddField_management,
#   CalculateField_management, arcpy.da.SearchCursor
# =============================================================================

import arcpy
import os
import datetime

# ---------------------------------------------------------------------------
# Configuration — update PROJECT_ROOT to match your machine
# ---------------------------------------------------------------------------

PROJECT_ROOT = r"C:\\arcgis pro arc py\\Toronto"
GDB_PATH     = os.path.join(PROJECT_ROOT, "ArcGIS", "Toronto_Pipeline.gdb")

ROADS_LAYER  = "Centreline___Version_2___4326"
WARDS_LAYER  = "City_Wards_Data___4326"
SOURCE_FIELD = "LINEAR_5"


# ---------------------------------------------------------------------------
# Audit coordinate systems across all layers in the GDB
# ---------------------------------------------------------------------------

def audit_layers(gdb_path):
    """
    Loops through every feature class in the GDB and reports its
    coordinate system. Flags anything not in NAD83 CSRS — the Canadian
    federal standard used by NRCan and most provincial agencies.

    WGS84 and NAD83 CSRS differ by ~1.5 metres in Ontario, which is
    acceptable for web mapping but not for infrastructure or surveying.
    """
    print(f"\n--- Layer Audit: {gdb_path} ---")
    print(f"    Run at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    arcpy.env.workspace = gdb_path
    feature_classes = arcpy.ListFeatureClasses()

    if not feature_classes:
        print("    No feature classes found. Check GDB_PATH.")
        return []

    flagged = []

    for fc in feature_classes:
        path  = os.path.join(gdb_path, fc)
        desc  = arcpy.Describe(path)
        sr    = desc.spatialReference
        count = int(arcpy.GetCount_management(path).getOutput(0))

        print(f"    {fc}")
        print(f"      Geometry : {desc.shapeType}")
        print(f"      Features : {count:,}")
        print(f"      CRS      : {sr.name} ({sr.type})")

        if "CSRS" not in sr.name:
            print(f"      Status   : NOT in NAD83 CSRS — flagged for reprojection")
            flagged.append(fc)
        else:
            print(f"      Status   : NAD83 CSRS confirmed")
        print()

    if flagged:
        print(f"    {len(flagged)} layer(s) flagged — will be reprojected in 03_reproject_nad83.py")
    else:
        print("    All layers in NAD83 CSRS.")

    return flagged


# ---------------------------------------------------------------------------
# Add STREET_NAME_CLEAN field and populate with Title Case
# ---------------------------------------------------------------------------

def clean_street_names(gdb_path, layer_name, source_field):
    """
    Adds STREET_NAME_CLEAN to the roads layer and calculates Title Case
    from the source field. Handles 64,659 road segments automatically.

    The Toronto Centreline stores full street names in LINEAR_5.
    Legacy municipal datasets commonly store names in ALL CAPS from
    older mainframe entry systems.
    """
    print("--- Street Name Standardization ---\n")

    roads_path = os.path.join(gdb_path, layer_name)

    if not arcpy.Exists(roads_path):
        print(f"    Layer not found: {layer_name}")
        return

    existing = [f.name for f in arcpy.ListFields(roads_path)]

    if source_field not in existing:
        print(f"    Source field '{source_field}' not found.")
        print(f"    Available fields: {existing}")
        return

    new_field = "STREET_NAME_CLEAN"

    if new_field not in existing:
        print(f"    Adding field: {new_field}")
        arcpy.management.AddField(
            in_table     = roads_path,
            field_name   = new_field,
            field_type   = "TEXT",
            field_length = 100,
            field_alias  = "Street Name (Clean)"
        )

    print(f"    Calculating Title Case from {source_field} ...")

    arcpy.management.CalculateField(
        in_table        = roads_path,
        field           = new_field,
        expression      = f"!{source_field}!.title()",
        expression_type = "PYTHON3"
    )

    # Print sample rows to verify output
    print(f"\n    Sample output (10 rows):")
    print(f"    {'Original':<40}  Clean")
    print(f"    {'-'*40}  {'-'*30}")

    count = 0
    with arcpy.da.SearchCursor(roads_path, [source_field, new_field]) as cursor:
        for row in cursor:
            original = row[0] or "(null)"
            cleaned  = row[1] or "(null)"
            print(f"    {original:<40}  {cleaned}")
            count += 1
            if count >= 10:
                break

    total = int(arcpy.GetCount_management(roads_path).getOutput(0))
    print(f"\n    Done — {total:,} segments updated.")


# ---------------------------------------------------------------------------
# Field inventory report
# ---------------------------------------------------------------------------

def field_inventory(gdb_path):
    print("--- Field Inventory ---\n")

    arcpy.env.workspace = gdb_path
    feature_classes = arcpy.ListFeatureClasses()   # ← store in variable first

    if not feature_classes:
        print("    No feature classes found.")
        return

    for fc in feature_classes:                     # ← loop over variable
        path = os.path.join(gdb_path, fc)
        print(f"    {fc}")
        print(f"    {'Field':<30} {'Type':<12} {'Length'}")
        print(f"    {'-'*30} {'-'*12} {'-'*8}")

        for field in arcpy.ListFields(path):
            if field.type not in ("Geometry", "OID"):
                print(f"    {field.name:<30} {field.type:<12} {field.length}")
        print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  Toronto Urban Data Pipeline — 01 Data Audit")
    print("=" * 60)

    arcpy.env.workspace        = GDB_PATH
    arcpy.env.overwriteOutput  = True

    audit_layers(GDB_PATH)
    clean_street_names(GDB_PATH, ROADS_LAYER, SOURCE_FIELD)
    field_inventory(GDB_PATH)

    print("\n" + "=" * 60)
    print("  Script complete — ready for 02_data_analysis.py")
    print("=" * 60 + "\n")

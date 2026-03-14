# =============================================================================
# Toronto Urban Data Pipeline
# Script 03 — Reprojection to NAD83 CSRS UTM Zone 17N
#
# Author  : Ibrahim Mirza
# Date    : 2026
#
# Description:
#   Detects the coordinate system of each input layer, calculates the
#   correct UTM zone from the dataset extent, and reprojects to
#   NAD83 CSRS — the Canadian federal datum maintained by Natural
#   Resources Canada. Applies the correct datum transformation to
#   avoid the ~1.5 metre shift that occurs when this step is omitted.
#
# Data Sources:
#   - Toronto Centreline (City of Toronto Open Data)
#   - City of Toronto Ward Boundaries (City of Toronto Open Data)
#
# Skills:
#   arcpy.Describe, arcpy.Project_management, arcpy.SpatialReference,
#   geo_transformation parameter, UTM zone calculation
# =============================================================================

import arcpy
import os
import math
import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

PROJECT_ROOT = r"C:\arcgis pro arc py\Toronto"
GDB_PATH     = os.path.join(PROJECT_ROOT, "ArcGIS", "Toronto_Pipeline.gdb")

# Input layers (WGS84 from Open Data portal)
ROADS_INPUT  = "Centreline___Version_2___4326"
WARDS_INPUT  = "City_Wards_Data___4326"

# Output layer names after reprojection
ROADS_OUTPUT = "Centreline_NAD83_UTM17N"
WARDS_OUTPUT = "City_Wards_NAD83_UTM17N"

# Datum transformation for WGS84 → NAD83 CSRS in Ontario
# Using the wrong transformation shifts data by up to 2 metres silently
TRANSFORMATION = "NAD_1983_CSRS_To_WGS_1984_2"


# ---------------------------------------------------------------------------
# Calculate the correct UTM zone from a layer's geographic extent
# ---------------------------------------------------------------------------

def get_utm_zone(gdb_path, layer_name):
    """
    Derives the UTM zone from the centre longitude of the dataset.

    Formula: zone = floor((longitude + 180) / 6) + 1

    Toronto at -79.38° → floor((100.62) / 6) + 1 = 17
    Ottawa  at -75.70° → floor((104.30) / 6) + 1 = 18
    Calgary at -114.0° → floor((66.00)  / 6) + 1 = 11
    """
    path = os.path.join(gdb_path, layer_name)
    desc = arcpy.Describe(path)
    ext  = desc.extent
    sr   = desc.spatialReference

    centre_lon = (ext.XMin + ext.XMax) / 2
    centre_lat = (ext.YMin + ext.YMax) / 2

    zone       = math.floor((centre_lon + 180) / 6) + 1
    hemisphere = "N" if centre_lat >= 0 else "S"
    crs_name   = f"NAD_1983_CSRS_UTM_Zone_{zone}{hemisphere}"

    print(f"    Layer       : {layer_name}")
    print(f"    Current CRS : {sr.name}")
    print(f"    Centre      : {round(centre_lat, 4)}°N, {round(centre_lon, 4)}°W")
    print(f"    UTM Zone    : {zone}{hemisphere}")
    print(f"    Target CRS  : {crs_name}\n")

    return crs_name


# ---------------------------------------------------------------------------
# Reproject a single layer
# ---------------------------------------------------------------------------

def reproject_layer(gdb_path, input_name, output_name, target_crs_name, transformation):
    """
    Reprojects input_name to target_crs_name and saves as output_name
    in the same GDB. Uses the specified datum transformation.

    The geo_transformation parameter is critical — omitting it causes
    arcpy to use a default that may not be appropriate for the input
    datum, resulting in a silent positional error.
    """
    input_path  = os.path.join(gdb_path, input_name)
    output_path = os.path.join(gdb_path, output_name)

    if arcpy.Exists(output_path):
        arcpy.management.Delete(output_path)

    try:
        target_sr = arcpy.SpatialReference(target_crs_name)
    except Exception as e:
        print(f"    Could not build SpatialReference for '{target_crs_name}': {e}")
        print(f"    Trying WKID 2958 (NAD83 CSRS UTM Zone 17N)...")
        target_sr = arcpy.SpatialReference(2958)

    print(f"    Reprojecting {input_name} ...")

    arcpy.management.Project(
        in_dataset       = input_path,
        out_dataset      = output_path,
        out_coor_system  = target_sr,
        transform_method = transformation
    )

    print(f"    Saved as: {output_name}")


# ---------------------------------------------------------------------------
# Verify output CRS and confirm extent is now in metres
# ---------------------------------------------------------------------------

def verify_reprojection(gdb_path, original, reprojected):
    """
    Compares the original and reprojected layers side by side.
    A successful reprojection will show extent values in metres
    (e.g. ~630,000 easting) rather than degrees (~-79°).
    """
    orig_desc = arcpy.Describe(os.path.join(gdb_path, original))
    repr_desc = arcpy.Describe(os.path.join(gdb_path, reprojected))

    orig_sr  = orig_desc.spatialReference
    repr_sr  = repr_desc.spatialReference
    orig_ext = orig_desc.extent
    repr_ext = repr_desc.extent

    print(f"    {'Property':<16} {'Before':<30} After")
    print(f"    {'-'*16} {'-'*30} {'-'*30}")
    print(f"    {'CRS':<16} {orig_sr.name:<30} {repr_sr.name}")
    print(f"    {'Type':<16} {orig_sr.type:<30} {repr_sr.type}")
    print(f"    {'XMin':<16} {str(round(orig_ext.XMin,4))+'°':<30} {str(round(repr_ext.XMin,1))+' m'}")
    print(f"    {'YMin':<16} {str(round(orig_ext.YMin,4))+'°':<30} {str(round(repr_ext.YMin,1))+' m'}")

    if "CSRS" in repr_sr.name and repr_sr.type == "Projected":
        print(f"\n    Verified — output is in NAD83 CSRS (projected, metres)")
    else:
        print(f"\n    WARNING — expected NAD83 CSRS Projected, got: {repr_sr.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  Toronto Urban Data Pipeline — 03 Reproject NAD83")
    print("=" * 60)

    arcpy.env.workspace       = GDB_PATH
    arcpy.env.overwriteOutput = True

    print("\n--- UTM Zone Detection ---\n")
    target_crs = get_utm_zone(GDB_PATH, ROADS_INPUT)

    print("--- Reprojection ---\n")
    reproject_layer(GDB_PATH, ROADS_INPUT, ROADS_OUTPUT, target_crs, TRANSFORMATION)
    reproject_layer(GDB_PATH, WARDS_INPUT, WARDS_OUTPUT, target_crs, TRANSFORMATION)

    print("\n--- Verification ---\n")
    print(f"  Roads:")
    verify_reprojection(GDB_PATH, ROADS_INPUT, ROADS_OUTPUT)
    print(f"\n  Wards:")
    verify_reprojection(GDB_PATH, WARDS_INPUT, WARDS_OUTPUT)

    print("\n" + "=" * 60)
    print("  Script complete — ready for 04_export_ward_maps.py")
    print("=" * 60 + "\n")

import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import interpolate
import simplekml
import xml.etree.ElementTree as ET
import csv
import os
import math
from scipy import interpolate


def destination_location(homeLattitude, homeLongitude, distance, bearing):
    R = 6371e3  # Radius of earth in metres
    rlat1 = homeLattitude * (math.pi / 180)
    rlon1 = homeLongitude * (math.pi / 180)
    d = distance
    bearing = bearing * (math.pi / 180)  # Converting bearing to radians
    rlat2 = math.asin(
        (math.sin(rlat1) * math.cos(d / R))
        + (math.cos(rlat1) * math.sin(d / R) * math.cos(bearing))
    )
    rlon2 = rlon1 + math.atan2(
        (math.sin(bearing) * math.sin(d / R) * math.cos(rlat1)),
        (math.cos(d / R) - (math.sin(rlat1) * math.sin(rlat2))),
    )
    rlat2 = rlat2 * (180 / math.pi)  # Converting to degrees
    rlon2 = rlon2 * (180 / math.pi)  # converting to degrees
    location = [rlat2, rlon2]
    return location


def gps_bearing(
    homeLattitude, homeLongitude, destinationLattitude, destinationLongitude
):
    R = 6371e3  # Radius of earth in metres
    rlat1 = homeLattitude * (math.pi / 180)
    rlat2 = destinationLattitude * (math.pi / 180)
    rlon1 = homeLongitude * (math.pi / 180)
    rlon2 = destinationLongitude * (math.pi / 180)
    dlat = (destinationLattitude - homeLattitude) * (math.pi / 180)
    dlon = (destinationLongitude - homeLongitude) * (math.pi / 180)
    # haversine formula to find distance
    a = (math.sin(dlat / 2) * math.sin(dlat / 2)) + (
        math.cos(rlat1) * math.cos(rlat2) * (math.sin(dlon / 2) * math.sin(dlon / 2))
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c  # distance in metres
    # formula for bearing
    y = math.sin(rlon2 - rlon1) * math.cos(rlat2)
    x = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(
        rlat2
    ) * math.cos(rlon2 - rlon1)
    bearing = math.atan2(y, x)  # bearing in radians
    bearingDegrees = bearing * (180 / math.pi)
    out = [distance, bearingDegrees]
    return out


def extract_data_from_kml(kml_file_path):
    # Open the KML file
    kml = simplekml.Kml()
    kml.open(kml_file_path)

    # Access features in the KML file
    for feature in kml.features():
        # Check if the feature is a placemark
        if isinstance(feature, simplekml.Placemark):
            placemark = feature
            # Extract placemark data
            name = placemark.name
            description = placemark.description
            coordinates = (
                placemark.geometry.coords
            )  # Coordinates in (longitude, latitude) format
            print("Name:", name)
            print("Description:", description)
            print("Coordinates:", coordinates)
            print("----------------------------------")


def kml_read(kml_file_path):
    tree = ET.parse(kml_file_path)
    root = tree.getroot()
    # result_array = [["latitude","longitude"]]
    result_array = []

    for placemark in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark"):
        name = placemark.find("{http://www.opengis.net/kml/2.2}name").text
        coordinates = placemark.find(
            ".//{http://www.opengis.net/kml/2.2}coordinates"
        ).text
        coordinates_list = coordinates.strip().split(" ")

        for coordinate_set in coordinates_list:
            lon, lat, alt = map(float, coordinate_set.split(","))
            result_array.append([lat, lon])

    return result_array


def cartToGeo(origin, endDistance, cartLocation):
    # The initial point of rectangle in (x,y) is (0,0) so considering the current
    # location as origin and retreiving the latitude and longitude from the GPS
    # origin = (12.948048, 80.139742) Format

    # Calculating the hypot end point for interpolating the latitudes and longitudes
    rEndDistance = math.sqrt(2 * (endDistance**2))

    # The bearing for the hypot angle is 45 degrees considering coverage area as square
    bearing = 45

    # Determining the Latitude and Longitude of Middle point of the sqaure area
    # and hypot end point of square area for interpolating latitude and longitude
    lEnd, rEnd = destination_location(
        origin[0], origin[1], rEndDistance, 180 + bearing
    ), destination_location(origin[0], origin[1], rEndDistance, bearing)

    # Array of (x,y)
    x_cart, y_cart = [-endDistance, 0, endDistance], [-endDistance, 0, endDistance]

    # Array of (latitude, longitude)
    x_lon, y_lat = [lEnd[1], origin[1], rEnd[1]], [lEnd[0], origin[0], rEnd[0]]

    # Latitude interpolation function
    f_lat = interpolate.interp1d(y_cart, y_lat)

    # Longitude interpolation function
    f_lon = interpolate.interp1d(x_cart, x_lon)

    # Converting (latitude, longitude) to (x,y) using interpolation function
    lat, lon = f_lat(cartLocation[1]), f_lon(cartLocation[0])
    return (lat, lon)


def generate_XY_Positions(numOfDrones, x, y, origin):
    endDistance = 100000
    Initial_x, Initial_y = x, y
    XY_values = []
    lat, lon = cartToGeo(origin, endDistance, [0, 0])
    XY_values.append([lat, lon])
    for i in range(numOfDrones - 1):
        lat, lon = cartToGeo(origin, endDistance, [Initial_x, Initial_y])
        XY_values.append([lat, lon])
        Initial_x += x
        Initial_y += y
    return XY_values

def Grid_Pattern(cols,rows,origin):
    home_positions = []
    for row in range(cols):
        XY_values = generate_XY_Positions(rows,0,-50,origin)
        for home_pos in XY_values:
            home_positions.append(home_pos)
        origin = cartToGeo(origin,10000,(-50,0))
    return home_positions


def VTOL_right_reverse(numOfDrones):
    result = kml_read(
        "C:/Users/vshar/OneDrive/Documents/fullstack/skybrush-server/src/flockwave/server/VTOL/kmls/Reverse-Mission.kml"
    )

    bearing = 0
    prev_bearing = 0
    #
    # x = 0
    # y = -60
    #
    lat_lons = [[] for _ in range(20)]
    #
    # prev_bearing = abs(
    #     gps_bearing(result[0][0], result[0][1], result[1][0], result[1][1])[1]
    # )
    # print("prevbearrrrrrrrrrrrrr", prev_bearing)
    # if prev_bearing >= -30 and prev_bearing <= 30:
    #     x = -60
    #     y = 0
    # elif prev_bearing >= 150 and prev_bearing <= 210:
    #     x = 60
    #     y = 0
    # elif prev_bearing >= -125 and prev_bearing <= -50:
    #     x = 60
    #     y = 0
    # elif prev_bearing >= 50 and prev_bearing <= 125:
    #     x = 0
    #     y = 60

    # print("xxxxxxxxxxxxxxxxxxxxxYYYYYYYYY", x, y)
    #
    # flag = 0
    # print(result)
    #
    # for index in range(len(result) - 1):
    #     bearing = gps_bearing(
    #         result[index][0],
    #         result[index][1],
    #         result[index + 1][0],
    #         result[index + 1][1],
    #     )[1]
    #
    #     if (
    #         prev_bearing >= -30
    #         and prev_bearing <= 30
    #         and bearing >= 50
    #         and bearing <= 125
    #     ):
    #         x = -60
    #         y = 60
    #     elif (
    #         prev_bearing >= 50
    #         and prev_bearing <= 125
    #         and bearing >= 150
    #         and bearing <= 210
    #     ):
    #         x = 60
    #         y = 60
    #     elif (
    #         prev_bearing >= 150
    #         and prev_bearing <= 210
    #         and bearing >= -125
    #         and bearing <= -50
    #     ):
    #         x = 60
    #         y = -60
    #     elif (
    #         prev_bearing >= 50
    #         and prev_bearing <= 125
    #         and bearing >= -30
    #         and bearing <= 30
    #     ):
    #         x = 60
    #         y = -60
    #     elif (
    #         prev_bearing >= -125
    #         and prev_bearing <= -50
    #         and bearing >= -30
    #         and bearing <= 30
    #     ):
    #         x = -60
    #         y = -60
    #     elif (
    #         prev_bearing >= -210
    #         and prev_bearing <= -150
    #         and bearing >= -125
    #         and bearing <= -50
    #     ):
    #         x = 60
    #         y = -60
    #     elif (
    #         prev_bearing >= 50
    #         and prev_bearing <= 125
    #         and bearing >= -210
    #         and bearing <= -125
    #     ):
    #         x = 60
    #         y = 60
    #     prev_bearing = bearing
    #
    #     res = generate_XY_Positions(numOfDrones, x, y, result[index])
    #     print("Resultttttttttttttt", res)
    #     flag += 1
    #     for i in range(len(res)):
    #         lat_lons[i].append(res[i])
    #
    # bearing = gps_bearing(
    #     result[len(result) - 2][0],
    #     result[len(result) - 2][1],
    #     result[len(result) - 1][0],
    #     result[len(result) - 1][1],
    # )[1]

    # if bearing >= -30 and bearing <= 30:
    #     x = -60
    #     y = 0
    # elif bearing >= 50 and bearing <= 125:
    #     x = 0
    #     y = 60
    # elif bearing >= -125 and bearing <= -50:
    #     x = 0
    #     y = -60
    # elif bearing >= -210 and bearing <= -130:
    #     x = 120
    #     y = 120

    # res = generate_XY_Positions(numOfDrones, x, y, result[len(result) - 1])

    for index in range(len(result)):
        positions = Grid_Pattern(2,5,result[index])
        for i in range(len(positions)):
            lat_lons[i].append(positions[i])

    for i in range(numOfDrones):
        with open(
            "C:/Users/vshar/OneDrive/Documents/fullstack/skybrush-server/src/flockwave/server/VTOL/csvs/reverse-drone-{}.csv".format(
                i + 1
            ),
            "w",
            newline="",
        ) as f:
            csvwriter = csv.writer(f)
            for j in range(len(lat_lons[i])):
                csvwriter.writerow([lat_lons[i][j][0], lat_lons[i][j][1]])

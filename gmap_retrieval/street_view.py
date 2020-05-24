import fnmatch
import json
import numpy as np
import numpy.random as npr
import pandas as pd
import os
from tqdm import tqdm
import urllib

def get_lat_lon(loc, d, tc):
    """Calculate the latitude and longitude of a place that is 'd' km away from 'loc' in direction 'tc'.

    Parameters
    ----------
    loc: str | list of str
        a location (or locations) specified by latitude and longitude
        each location needs to be a comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"
    d: float | list of float
        a distance (or distances) in km from 'loc' to a place to be returned by this function
    tc: float | list of float
        a direction (or directions) in radians

    Returns
    -------
    lat_lon: pandas Series of str
        location(s), specified by latitude and longitude, that is 'd' km away from 'loc' in direction 'tc'
        each location needs to be a comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"
    """
    if type(d) != type(tc):
        raise ValueError("d and tc has to be same type: float or list of float.")

    elif type(loc)==str:
        if type(d)==float:
            loc = [loc]
            d = [d]
            tc =[tc]

    elif type(d) == float:
        raise TypeError("If type of loc is list, type of d and tc have to be both list of float.")

    elif len(loc)!=len(d) or len(loc)!=len(tc) or len(d)!=len(tc):
        raise ValueError("The lengths of loc, d and tc have to be same.")

    loc = np.array([loc.split(",")], dtype=float)
    d = np.array(d)
    tc = np.array(tc)

    # convert from km to radians
    d = d/6371

    loc = loc*np.pi/180
    lat1 = loc[:, 0]
    lon1 = loc[:, 1]

    lat = np.arcsin(np.sin(lat1) * np.cos(d) + np.cos(lat1) * np.sin(d) * np.cos(tc))
    dlon = np.arctan2(np.sin(tc) * np.sin(d) * np.cos(lat1), np.cos(d) - np.sin(lat1) * np.sin(lat))
    lon = (lon1 - dlon + np.pi) % (2 * np.pi) - np.pi

    lat_lon = pd.Series((lat * 180 / np.pi), dtype=str) + "," + pd.Series((lon * 180 / np.pi), dtype=str)

    return lat_lon

def is_gsv_available(API_key, loc, search_radius, outdoor, limit=None):
    """Check if Google street view image is available around specific location(s).
    Check https://developers.google.com/maps/documentation/streetview/metadata for details of API.

    Parameters
    ----------
    API_key: str
        key for Google Map API
    loc: numpy chararray
        location(s) specified by latitude and longitude
        each location needs to be a comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"
    search_radius: int
        a radius, specified in meters, in which to search for a panorama, centered on the given latitude and longitude
    outdoor: boolean
        whether or not to limit the search to outdoor photos
    limit: int | None
        the number of "OK" status of locations after which the function stops finding the status of further locations
        if None, no limit is set

    Returns
    -------
    availability: list of boolean
        a list of whether a Google street view image is available around specific location(s)
    """
    if limit == None:
        limit = len(loc)

    prefix = "https://maps.googleapis.com/maps/api/streetview/metadata?"
    location = "location=" + loc
    if outdoor:
        source = "&source=outdoor"
    else:
        source = ""
    radius = "&radius=" + str(search_radius)
    key = "&key=" + API_key

    urls = prefix + location + source + radius + key

    availability = [False]*len(urls)
    count = 0
    for i, url in enumerate(urls):
        while True:
            try:
                # get API response
                response = urllib.request.urlopen(url)
            except IOError:
                pass # retry
            else: # if no IOError occurs
                status = json.loads(response.read().decode('utf-8'))['status']
                availability[i] = (status=='OK')
                break
        if availability[i]:
            count += 1
        if count == limit:
            return availability
    return availability

def get_street_view_image(directory_name, API_key, IDs, latitude_longitude, n_images, rad=1, camera_direction=-1,
                          field_of_view=120, angle=0, search_radius=50, outdoor=True, image_size="640x640",
                          limit=10, print_progress=True, if_jupyter=False):
    """Save Google Street View images around specified locations using Street View Satatic API.

    Parameters
    ----------
    directory_name: str
        name of a new directory containing all the saved images
    API_key: str
        key for Google Map API
    IDs: pandas Series [n_locations]
        list of IDs that identify locations
    latitude_longitude: pandas Series [n_locations]
        list of locations specified by latitude and longitude;
        each location needs to take the form of comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"
    n_images: int
        the number of Google Street View images to be fetched for each ID
    rad: int, optional (default=1)
        radius, specified in km, of a circle around the location, specified by latitude and longitude, in which
        the Google Street View images are fetched
    camera_direction: int, optional (default=-1)
        the compass heading of the camera
        Accepted values are from 0 to 360 (both values indicating North, with 90 indicating East, and 180 South),
        -1, indicating random selection of headinv value from 0 to 360, and
        -2, indicating the heading value calculated to direct the camera
        towards the location specified by latitude and longitude
    field_of_view: int, optional (default=120)
        the horizontal field of view of the image; maximum is 120
    angle: int, optional (default=0)
        the up or down angle of the camera relative to the Street View vehicle:
        Positive values angle the camera up (with 90 degrees indicating straight up)
        and negative values angle the camera down (with -90 indicating straight down)
    search_radius: int, optional (default=50)
        a radius, specified in meters, in which to search for a panorama, centered on the given latitude and longitude
    outdoor: boolean, optional (default=True)
        whether or not to limit the search to outdoor photos
    image_size: str, optional (default="400x400")
        the rectangular dimensions of the map image;  takes the form {horizontal_value}x{vertical_value}
    limit: int
        limit the number of trials to find GSV images
        n_images * limit would be the number of candidate locations to check if GSV available around the area
    print_progress: boolean, optional (default=True)
        whether or not to print the progress bar of the data retrieval
    if_jupyter: boolean, optional (default=False)
        whether or not the program is running on Jupyter; this matters only if print_progress==True
    """
    if len(IDs) != len(latitude_longitude):
        raise ValueError("The lengths of IDs and latitude_longitude have to be same.")

    if if_jupyter:
        from tqdm.notebook import tqdm

    # create directory in which all the images are saved
    if not os.path.exists(directory_name):
        os.mkdir(directory_name)

    # go through each specified location
    if print_progress:
        bar = tqdm(total=len(IDs) * n_images, mininterval=0, maxinterval=10, miniters=1)
    for i in range(len(IDs)):
        ID = str(IDs[i])
        lat_lon = latitude_longitude[i]

        # create a sub-directory in which 'n_images' Google Street View images around the specified location are saved
        sub_dir = f"{directory_name}/{ID}"

        # if the sub-directory doesn't exist, create a new one
        if not os.path.exists(sub_dir):
            os.mkdir(sub_dir)
            n_existing_images = 0

        else: # if there are already n_images png images in the sub-directory
            n_existing_images = len(fnmatch.filter(os.listdir(sub_dir), '*.png'))
            if n_existing_images == n_images:
                if print_progress:
                    bar.update(n_images)
                continue
            else: # if there are some images saved previously, but less than 'n_images'
                if print_progress:
                    bar.update(n_existing_images)
                pass

        # randomly pick 'n_images' locations within 'radius' km radius
        count = n_images
        trial_count = 0
        candidate_multiple = 1.5
        while True:
            # randomly pick 'n_images' * 'candidate_multiple' candidates for locations around 'lat_lon'
            direction = npr.uniform(0, 2 * np.pi, int(n_images*candidate_multiple))
            distance = npr.uniform(0, rad, int(n_images*candidate_multiple))
            loc = get_lat_lon(lat_lon, distance, direction)
            # check if GSV is available for randonly picked 'n_images' * 1.5 locations
            available = is_gsv_available(API_key, loc, search_radius, outdoor, count)
            loc_valid_new = loc[available].reset_index(drop=True)
            try: # case of the non-first loop
                loc_valid = loc_valid.append(loc_valid_new, ignore_index)
            except NameError: # case of the first loop
                loc_valid = loc_valid_new
            if len(loc_valid) >= n_images: # when having enought locations
                loc_valid = loc_valid[:count]
                break
            elif n_images * limit < trial_count: # if there are not enough locations where GSV images are available
                print(f"After checking {trial_count} locations for GSV images, only {len(loc_valid)} GSV images found around the location where ID = {ID}")
                break
            else: # if not enough available locations are randomly chosen yet, go back to get candidates
                count -= len(loc_valid)
                trial_count += n_images * candidate_multiple

        # crate URLs
        # check https://developers.google.com/maps/documentation/streetview/intro for details of API
        prefix = "https://maps.googleapis.com/maps/api/streetview?"
        location = "location=" + loc_valid
        size = "&size=" + image_size
        if camera_direction == -2:
            heading = ""
        elif camera_direction == -1:
            heading = "&heading=" + pd.Series(npr.uniform(0, 360, len(location)).astype(str))
        else: #when camera_direction is given
            heading = "&heading=" + pd.Series(camera_direction)
        fov = "&fov=" + str(field_of_view)
        pitch = "&pitch=" + str(angle)
        radius = "&radius=" + str(search_radius)
        if outdoor:
            source = "&source=outdoor"
        else:
            source = ""
        key = "&key=" + API_key

        urls = prefix + location + size + heading + fov + pitch + radius + source + key

        skip_image = np.zeros(len(urls))
        # get and save Street View images using Google Street View Static API
        for j in range(len(urls)):
            url = urls[j]
            file_name = f"{sub_dir}/image{j}.png"
            # if a spacific image already exists
            if os.path.exists(file_name):
                skip_image[j] = 1

            else:
                while True:
                    try:
                        # get API response
                        image = urllib.request.urlopen(url).read()
                    except IOError:
                        pass # retry
                    else:
                        # save the png image
                        with open(file_name, mode="wb") as f:
                            f.write(image)
                        break
            if print_progress:
                bar.update(1)

        # save a CSV file that contains location information about the saved street view images
        loc_data = pd.DataFrame({'name': "image" + pd.Series(range(len(urls))).astype(str)[skip_image==0] + ".png",
                                  'location': np.array(loc_valid)[skip_image==0]})

        csv_path = f"{sub_dir}/loc.csv"
        if os.path.exists(csv_path):
            with open(csv_path, "a") as f:
                loc_data.to_csv(f, index=False, header=False)
        else:
            with open(csv_path, 'w') as f:
                loc_data.to_csv(f, index=False)

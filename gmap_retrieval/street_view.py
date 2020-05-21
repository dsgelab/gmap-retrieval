import fnmatch
import json
import numpy as np
import numpy.random as npr
import pandas as pd
import os
import urllib

def get_lat_lon(loc, d, tc):
    """Calculate the latitude and longitude of a place that is 'd' km away from 'loc' in direction 'tc'.

    Parameters
    ----------
    loc: str
        a location specified by latitude and longitude
        need to be a comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"
    d: float
        a distance in km from 'loc' to a place to be returned by this function
    tc: float
        a direction in radians

    Returns
    -------
    lat_lon: str
        a location, specified by latitude and longitude, that is 'd' km away from 'loc' in direction 'tc'
        a comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"
    """
    # convert from km to radians
    d = d/6371

    loc = loc.split(',')
    lat1 = float(loc[0])*np.pi/180
    lon1 = float(loc[1])*np.pi/180

    lat = np.arcsin(np.sin(lat1)*np.cos(d) + np.cos(lat1)*np.sin(d)*np.cos(tc))
    dlon = np.arctan2(np.sin(tc)*np.sin(d)*np.cos(lat1), np.cos(d) - np.sin(lat1)*np.sin(lat))
    lon = (lon1 - dlon + np.pi) % (2*np.pi) - np.pi

    lat_lon = str(lat*180/np.pi) + "," + str(lon*180/np.pi)

    return lat_lon

def get_street_view_metadata(API_key, loc):
    """Retrieve metadata of street view image around a specific location.

    Parameters
    ----------
    API_key: str
        key for Google Map API
    loc: str
        a location specified by latitude and longitude
        need to be a comma-separated {latitude,longitude} pair; e.g. "40.714728,-73.998672"

    Returns
    -------
    data: dict
        metadata of a specific location on Google Street View API
    """
    prefix = "https://maps.googleapis.com/maps/api/streetview/metadata?"
    location = "location=" + loc
    key = "&key=" + API_key

    url = prefix + location + key

    while True:
        try:
            # get API response
            response = urllib.request.urlopen(url)
        except IOError:
            pass # retry
        else: # if no IOError occurs
            data = json.loads(response.read().decode('utf-8'))
            break

    return data

def get_street_view_image(directory_name, API_key, IDs, latitude_longitude, n_images, rad=1, camera_direction=-1,
                          field_of_view=120, angle=0, search_radius=100, image_type="outdoor", image_size="640x640",
                          print_progress):
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
        the horizontal field of view of the image; maxmum is 120
    angle: int, optional (default=0)
        the up or down angle of the camera relative to the Street View vehicle:
        Positive values angle the camera up (with 90 degrees indicating straight up)
        and negative values angle the camera down (with -90 indicating straight down)
    search_radius:str, optional (default=50)
        a radius, specified in meters, in which to search for a panorama, centered on the given latitude and longitude
    image_type: str, optional (default="outdoor")
        a type of images retrieved, either "default", which includes any type of photos, or "outdoor"
    image_size: str, optional (default="400x400")
        the rectangular dimensions of the map image;  takes the form {horizontal_value}x{vertical_value}
    print_progress: boolean, optional (default=True)
        whether or not to print the progress of the data retrieval
    """
    # create directory in which all the images are saved
    if not os.path.exists(directory_name):
        os.mkdir(directory_name)

    # go through each specified location
    for i in range(len(IDs)):
        ID = str(IDs[i])
        lat_lon = latitude_longitude[i]

        # create a sub-directory in which 'n_images' Google Street View images around the specified location are saved
        sub_dir = f"{directory_name}/{ID}"
        if not os.path.exists(sub_dir):
            # if the sub-directory doesn't exist, create a new one
            os.mkdir(sub_dir)
        elif len(fnmatch.filter(os.listdir(sub_dir), '*.png')) == n_images:
            # if there are already n_images png images in the sub-directory
            if print_progress:
                print(f"The directory {sub_dir} already has {n_images} images!")
            continue
        else:
            pass

        # randomly pick 'n_images' locations within 'radius' km radius
        locations = [""]*n_images
        for j in range(n_images):
            while True:
                direction = npr.uniform(0, np.pi)
                distance = npr.uniform(0, rad)
                loc = get_lat_lon(lat_lon, distance, direction)
                metadata = get_street_view_metadata(API_key, loc)
                if metadata['status'] == 'OK':
                    break
            locations[j] = loc

        # crate URLs
        # check https://developers.google.com/maps/documentation/streetview/intro for details of API
        prefix = "https://maps.googleapis.com/maps/api/streetview?"
        location = "location=" + pd.Series(locations)
        size = "&size=" + image_size
        if camera_direction == -2:
            heading = ""
        elif camera_direction == -1:
            heading = "&heading=" + pd.Series(npr.uniform(0, 360, n_images).astype(str))
        else: #when camera_direction is given
            heading = "&heading=" + pd.Series(camera_direction)
        fov = "&fov=" + str(field_of_view)
        pitch = "&pitch=" + str(angle)
        radius = "&radius=" + str(search_radius)
        source = "&source=" + image_type
        key = "&key=" + API_key

        urls = prefix + location + size + heading + fov + pitch + radius + source + key

        skip_image = np.zeros(n_images)
        # get and save Street View images using Google Street View Static API
        for j in range(len(urls)):
            url = urls[j]
            file_name = f"{sub_dir}/image{j}.png"
            if os.path.exists(file_name):
                if print_progress:
                    print(f"...{file_name} already exists.")
                skip_image[j] = 1

            else:
                while True:
                    try:
                        # get API response
                        if print_progress:
                            print(f"API request made: {ID}-image{j}")
                        image = urllib.request.urlopen(url).read()
                    except IOError:
                        pass # retry
                    else:
                        # save the png image
                        if print_progress:
                            print(f"...Save {file_name}.")
                        with open(file_name, mode="wb") as f:
                            f.write(image)
                        break

        # save a CSV file that contains location information about the saved street view images
        locations = pd.DataFrame({'name': "image" + pd.Series(range(10)).astype(str)[skip_image==0] + ".png",
                                  'location': np.array(locations)[skip_image==0]})

        csv_path = f"{sub_dir}/loc.csv"
        if os.path.exists(csv_path):
            with open(csv_path, "a") as f:
                locations.to_csv(f, index=False, header=False)
        else:
            with open(csv_path, 'w') as f:
                locations.to_csv(f, index=False)
        if print_progress:
            print(f"Finished retrieving street view images for {ID}!\n")

import numpy as np
import os
import pandas as pd
import urllib

def find_zoom_level(latitudes, ideal_side_length, pixels_per_side):
    """Find the best matching zoom level for Google Maps Static API.

    Parameters
    ----------
    latitudes: pandas.Series, [n_places]
        list of latitudes for the centers of satellite images
    ideal_side_length: int
        ideal side length of an satellite image in km
    pixels_per_side: int
        pixels per side of an satellite image

    Returns
    -------
    zoom_levels: np.array, [n_places]
        list of best zoom levels for places
    side_lengths: np.array, [n_places]
        list of side lengths of expected satellite images given zoom_levels
    """

    # sort 'latitudes' from low to high with its original indices
    sorted_latitudes = sorted(zip(latitudes, range(len(latitudes))), key=lambda pair: pair[0])

    zoom_levels = np.zeros(len(latitudes))
    side_lengths = np.zeros(len(latitudes))

    best_zoom = 1
    for pair in sorted_latitudes:
        lat = pair[0]
        index = pair[1]
        for zoom in range(best_zoom-1, 22):
            meter_per_pixel = 156543.03392 * np.cos(lat * np.pi / 180) / (2**zoom)
            km_per_image = meter_per_pixel * pixels_per_side / 1000
            if km_per_image > ideal_side_length: # covered area is still too large
                previous_ratio = km_per_image**2 / ideal_side_length**2
                previous_km_per_image = km_per_image
            else: # now covered area is too small
                ratio = ideal_side_length**2 / km_per_image**2
                break
        if ratio <= previous_ratio:
            best_zoom = zoom
            side_length = km_per_image
        else:
            best_zoom = zoom - 1
            side_length = previous_km_per_image
        zoom_levels[index] = best_zoom
        side_lengths[index] = side_length

    return zoom_levels.astype(int), side_lengths

def get_satellite_image(directory_name, API_key, IDs, latitude_longitude, side_length=2, image_size="640x640", image_scale=1,
                        image_format="png", print_progress=True):
    """Save satellite images for specified locations using Google Maps Satatic API.

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
    side_length: int, optional (default=2)
        ideal side length of an image in km;
        saved image will NOT have side_length same as side_length but will have a similar side length
    image_size: str, optional (default="400x400")
        the rectangular dimensions of the map image; takes the form {horizontal_value}x{vertical_value}
    image_scale: int, optional (default=1)
        scaling on the size
    image_format: str, optional (default="png")
        format of output images
    print_progress: boolean, optional (default=True)
        whether or not to print the progress of the data retrieval
    """
    # find the best zoom levels to feed into Google Maps Static API and resulting side lengths of satellite images
    latitudes = latitude_longitude.apply(lambda x: x.split(",")[0]).astype(float)
    zoom_levels, side_lengths = find_zoom_level(latitudes, 2, 400)

    # crate URLs
    prefix = "https://maps.googleapis.com/maps/api/staticmap?"
    center = "center=" + latitude_longitude
    zoom = "&zoom=" + pd.Series(zoom_levels, dtype=str)
    size = "&size=" + image_size
    scale = "&scale=" + str(image_scale)
    form = "&format=" + image_format
    maptype = "&maptype=" + "satellite"
    key = "&key=" + API_key

    urls = prefix + center + zoom + size + scale + form + maptype + key

    # create a directory to save satellite images
    if not os.path.exists(directory_name):
        os.mkdir(directory_name)
        csv_exist = False
    else:
        csv_exist = True

    skip_id = np.zeros(len(IDs))
    # get and save satellite images using Google Maps Static API
    for i in range(len(IDs)):
        url = urls[i]
        file_name = directory_name + "/" + str(IDs[i]) + ".png"

        if os.path.exists(file_name):
            if print_progress:
                print(f"{file_name} already exists.")
            skip_id[i] = 1
        else:
            while True:
                try:
                    # get API response
                    if print_progress:
                        print(f"API request made: {IDs[i]}")
                    image = urllib.request.urlopen(url).read()
                except IOError:
                    pass # retry
                else:
                    # save the png image
                    if print_progress:
                        print(f"   Satellite image saved: {file_name}")
                    with open(file_name, mode="wb") as f:
                        f.write(image)
                    break

    # save actual side lengths of saved satellite images
    side_lengths = pd.DataFrame({'id': IDs[skip_id==0], 'side_length': side_lengths[skip_id==0]})

    if csv_exist:
        with open(f"{directory_name}/side_lengths.csv", "a") as f:
            side_lengths.to_csv(f, index=False, header=False)

    else:
        with open(f"{directory_name}/side_lengths.csv", "w") as f:
            side_lengths.to_csv(f, index=False)

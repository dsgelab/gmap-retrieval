import base64
import contextlib
import fnmatch
import hashlib
import hmac
import joblib
from joblib import Parallel, delayed
import json
import numpy as np
import numpy.random as npr
import pandas as pd
import os
from tqdm.auto import tqdm
import urllib
import urllib.parse as urlparse

def sign_url(input_urls=None, secret=None):
    """ Sign a request URL with a URL signing secret.
    Based on code from
    https://developers.google.com/maps/documentation/streetview/get-api-key.

    Parameters
    ----------
    input_urls: str | pandas Series of str
        The URL to sign
    secret: str
        Your URL signing secret

    Returns
    -------
    signed_urls: list of str
        The signed request URL
    """

    if (input_urls is None) or (secret is None):
        raise Exception("Both input_urls and secret are required")

    if type(input_urls) is str:
        input_urls = pd.Series([input_urls])

    signed_urls = [""]*len(input_urls)
    for i, input_url in enumerate(input_urls):
        url = urlparse.urlparse(input_url)

        # We only need to sign the path+query part of the string
        url_to_sign = url.path + "?" + url.query

        # Decode the private key into its binary format
        # We need to decode the URL-encoded private key
        decoded_key = base64.urlsafe_b64decode(secret)

        # Create a signature using the private key and the URL-encoded
        # string using HMAC SHA1. This signature will be binary.
        signature = hmac.new(decoded_key, str.encode(url_to_sign), hashlib.sha1)

        # Encode the binary signature into base64 for use within a URL
        encoded_signature = base64.urlsafe_b64encode(signature.digest())

        original_url = (url.scheme + "://" + url.netloc + url.path + "?"
                        + url.query)

        signed_urls[i] = (original_url + "&signature="
                          + encoded_signature.decode())

    # Return signed URL
    return signed_urls

def get_lat_lon(loc, d, tc):
    """Calculate the latitude/longitude of place(s)
    that is 'd' km away from 'loc' in direction 'tc'.

    Parameters
    ----------
    loc: str | list of float
        A location (or locations) specified by latitude and longitude
        needs to be a comma-separated {latitude,longitude} pair;
        e.g. "40.714728,-73.998672"
        If list, lengths must be same as that of 'd' and 'tc'.
    d: float | list of float
        A distance (or distances) in km from 'loc' to a place to be returned
        by this function.
        If list, length has to be same as that of 'tc' in case of list.

    tc: float | list of float
        A direction (or directions) in radians.
        If list, length has to be same as that of 'd' in case of list.

    Returns
    -------
    lat_lon: pandas Series of str
        location(s), specified by latitude and longitude,
        that is 'd' km away from 'loc' in direction 'tc'
        each location needs to be a comma-separated {latitude,longitude} pair;
        e.g. "40.714728,-73.998672"
    """
    # if d is array-like
    if hasattr(d, '__len__'):
        if not hasattr(tc, '__len__'):
            raise ValueError("d and tc needs be both float "
                             "or both array-like.")
        elif len(d) != len(tc):
            raise ValueError("The lengths of d and tc needs to be same.")

    # if loc is array-like
    if hasattr(loc, '__len__') and not isinstance(loc, str):
        if not hasattr(d, '__len__'):
            raise ValueError("If loc is array-like, both d and tc need to be "
                             "array-like with same length.")
        if len(loc) != len(d):
            raise ValueError("If loc is array-like, both d and tc need to be "
                             "array-like with same length.")

    # if loc is not array-like
    else:
        if hasattr(d, '__len__'):
            loc = [loc] * len(d)

        else: # if d and tc is not array-like
            d = [d]
            tc = [tc]


    circumference = 40075 #km
    if any(np.array(d) > circumference / 2):
        raise ValueError("Distance must be smaller "
                         f"than {circumference / 2}.")

    if any(np.logical_or(np.array(tc) < 0, np.array(tc) > 2 * np.pi)):
        raise ValueError("Direction must be between 0 to 2 * Pi.")

    loc = np.array([l.split(",") for l in loc], dtype=float)
    d = np.array(d)
    tc = np.array(tc)

    # convert from km to radians
    r = 6371 # radius of the earth in km
    d = d / r

    loc = loc * np.pi / 180
    lat1 = loc[:, 0]
    lon1 = loc[:, 1]

    lat = np.arcsin(np.sin(lat1) * np.cos(d)
          + np.cos(lat1) * np.sin(d) * np.cos(tc))
    dlon = np.arctan2(np.sin(tc) * np.sin(d) * np.cos(lat1),
                      np.cos(d) - np.sin(lat1) * np.sin(lat))
    lon = (lon1 - dlon + np.pi) % (2 * np.pi) - np.pi

    lat_lon = (pd.Series((lat * 180 / np.pi), dtype=str) + "," +
               pd.Series((lon * 180 / np.pi), dtype=str))

    return lat_lon

def is_gsv_available(API_key, loc, search_radius, outdoor, limit=None):
    """Check if Google street view image is available given location(s).
    Check https://developers.google.com/maps/documentation/streetview/metadata
    for details of Google Map API used in this function.

    Parameters
    ----------
    API_key: str
        Key for Google Map API.
    loc: numpy.chararray
        Location(s) specified by latitude and longitude.
        Each location needs to be a comma-separated {latitude,longitude} pair;
        e.g. "40.714728,-73.998672"
    search_radius: int
        A radius, specified in meters, in which to search for a panorama,
        centered on the given latitude and longitude.
    outdoor: boolean
        Whether or not to limit the search to outdoor photos.
    limit: int | None
        The number of "OK" status of locations after which
        the function stops checking the status of further locations.
        If None, the status of all the given locations are checked and returned.

    Returns
    -------
    availability: list of boolean
        A list of whether a Google street view image is available
        around specific location(s).
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

def get_street_view_image(directory_name, API_key, IDs,
                          latitude_longitude, n_images, secret=None, rad=1,
                          camera_direction=-1, field_of_view=120, angle=0,
                          search_radius=10, outdoor=True,
                          image_size="640x640", limit=10, n_jobs=1,
                          verbose=True):
    """Save Google Street View images around specified locations
    using Street View Satatic API.

    Parameters
    ----------
    directory_name: str
        Name of a new directory containing all the saved images.
        If the directory doesn't exist, creates a new one.
    API_key: str
        Key for Google Map API
    IDs: pandas Series [n_locations]
        List of IDs that identify locations.
    latitude_longitude: pandas Series [n_locations]
        List of locations specified by latitude and longitude;
        Each location needs to take the form of
        comma-separated {latitude,longitude} pair;
        e.g. "40.714728,-73.998672".
    n_images: int
        The number of Google Street View images to be fetched for each ID.
    secret: str | None, optional (defalut=None)
        Signature to authenticate Google static street view API requests.
        If None, no digital signature is used.
        If retrieving large amount of data, this variable might be required;
        Check https://developers.google.com/maps/documentation/streetview/usage-and-billing#authenticating-requests
    rad: int, optional (default=1)
        Radius, specified in km, of a circle around the location,
        specified by latitude and longitude, in which
        the Google Street View images are fetched.
    camera_direction: int, optional (default=-1)
        The compass heading of the camera.
        Accepted values are from 0 to 360.
        (Both values indicating North, with 90 indicating East, and 180 South),
        -1, indicating random selection of headinv value from 0 to 360, and
        -2, indicating the heading value calculated to direct the camera
        towards the location specified by latitude and longitude.
    field_of_view: int, optional (default=120)
        The horizontal field of view of the image; maximum is 120.
    angle: int, optional (default=0)
        The up / down angle of the camera relative to the Street View vehicle:
        Positive values angle the camera up
        (with 90 degrees indicating straight up)
        and negative values angle the camera down
        (with -90 indicating straight down)
    search_radius: int, optional (default=50)
        A radius, specified in meters, in which to search for a panorama,
        centered on the given latitude and longitude.
    outdoor: boolean, optional (default=True)
        Whether or not to limit the search to outdoor photos.
    image_size: str, optional (default="400x400")
        The rectangular dimensions of the map image;
        Takes the form {horizontal_value}x{vertical_value}.
    limit: int, optional (default=10)
        Limit the number of trials to find GSV images.
        n_images * limit would be the number of candidate locations
        to check if GSV available around the area.
    n_jobs: int, optional (default=1)
        The number of processes (=number of CPU cores) to use.
        Specify -1 to use all available cores.
    verbose: boolean, optional (default=True)
        Whether or not to print the progress bar of the data retrieval.
    """
    if len(IDs) != len(latitude_longitude):
        raise ValueError("The lengths of IDs and latitude_longitude have"
                         "to be same.")

    # create directory in which all the images are saved
    if not os.path.exists(directory_name):
        os.mkdir(directory_name)

    @contextlib.contextmanager
    def tqdm_joblib(tqdm_object):
        """Context manager to patch joblib to report into tqdm progress bar"""
        class TqdmBatchCompletionCallback(joblib.parallel.BatchCompletionCallBack):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def __call__(self, *args, **kwargs):
                tqdm_object.update(n=self.batch_size)
                return super().__call__(*args, **kwargs)

        old_batch_callback = joblib.parallel.BatchCompletionCallBack
        joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback
        try:
            yield tqdm_object
        finally:
            joblib.parallel.BatchCompletionCallBack = old_batch_callback
            tqdm_object.close()

    def collect_gsv_images_for_each_id(i): # go through each specified location
        id_ = str(IDs[i])
        loc = latitude_longitude[i]

        # create a sub-directory in which 'n_images' Google Street View images
        # around the specified location are saved
        sub_dir = f"{directory_name}/{id_}"

        # if the sub-directory doesn't exist, create a new one
        if not os.path.exists(sub_dir):
            os.mkdir(sub_dir)
            n_existing_images = 0

        else: # if there are already n_images png images in the sub-directory
            n_existing_images = len(fnmatch.filter(os.listdir(sub_dir),
                                                   '*.png'))
            if n_existing_images == n_images: # if there are 'n_images' images in the sub directory
                return
            else: # if there are some images saved previously, but less than 'n_images'
                pass

        # randomly pick 'n_needed_images' locations within 'radius' km radius
        n_needed_images = n_images - n_existing_images
        count = n_needed_images
        trial_count = 0
        candidate_multiple = 1.5
        while True:
            # randomly pick 'n_needed_images' * 'candidate_multiple'
            # candidates for locations around 'loc'
            direction = npr.uniform(0, 2 * np.pi,
                                    int(n_images * candidate_multiple))
            distance = (np.sqrt(npr.uniform(0,
                                            1,
                                            int(n_images * candidate_multiple)))
                                            * rad)
            lat_lon = get_lat_lon(loc, distance, direction)
            # check if GSV is available for randonly picked
            # 'n_needed_images' * 'candidate_multiple' locations
            available = is_gsv_available(API_key, lat_lon, search_radius,
                                         outdoor, n_images)
            loc_valid_new = lat_lon[available].reset_index(drop=True)
            try: # case of the non-first loop
                loc_valid = loc_valid.append(loc_valid_new, ignore_index)
            except NameError: # case of the first loop
                loc_valid = loc_valid_new
            if len(loc_valid) >= n_needed_images: # when having enough locations
                loc_valid = loc_valid[:n_needed_images]
                count = 0
                break
            # if there are not enough locations where GSV images are available
            elif n_images * limit < trial_count:
                print(f"After checking {trial_count} locations for GSV images,"
                      f"only {len(loc_valid)}"
                      f"+ pre-existing {n_existing_images}"
                      f"GSV images found around the location where id_ = {id_}")
                count -= len(loc_valid_new)
                break
            # if not enough available locations are randomly chosen yet
            else:
                trial_count += n_images * candidate_multiple
                count -= len(loc_valid_new)

        # crate URLs
        # check
        # https://developers.google.com/maps/documentation/streetview/intro
        # for details of API
        prefix = "https://maps.googleapis.com/maps/api/streetview?"
        location = "location=" + loc_valid
        size = "&size=" + image_size
        if camera_direction == -2:
            heading = ""
        elif camera_direction == -1:
            heading = ("&heading="
                       + pd.Series(npr.uniform(0,
                                               360,
                                               len(location)).astype(str)))
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

        urls = (prefix + location + size + heading + fov
                + pitch + radius + source + key)

        # add digital signature if provided
        if secret is not None:
            urls = sign_url(urls, secret)

        # get and save Street View images using Google Street View Static API
        new_file_names = [""]*len(urls)
        j = 0
        for k, url in enumerate(urls):
            while True: # find unused file name
                file_name = f"{sub_dir}/image{j}.png"
                if os.path.exists(file_name):
                    j += 1
                else:
                    new_file_names[k] = f"image{j}.png"
                    break

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

        # save a CSV file that contains location information
        # about the saved street view images
        loc_data = pd.DataFrame({'name': new_file_names,
                                 'location': loc_valid})

        csv_path = f"{sub_dir}/loc.csv"
        if os.path.exists(csv_path):
            with open(csv_path, "a") as f:
                loc_data.to_csv(f, index=False, header=False)
        else:
            with open(csv_path, 'w') as f:
                loc_data.to_csv(f, index=False)

    if verbose: # with progress bar
        with tqdm_joblib(tqdm(desc='Data Retrieval Progress', total=len(IDs))) as progress_bar:
            Parallel(n_jobs) (delayed(collect_gsv_images_for_each_id)(i) for i in range(len(IDs)))
    else: # without progress bar
        Parallel(n_jobs) (delayed(collect_gsv_images_for_each_id)(i) for i in range(len(IDs)))

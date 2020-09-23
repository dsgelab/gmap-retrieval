import contextlib
import joblib
from joblib import Parallel, delayed
import numpy as np
import os
import pandas as pd
from tqdm.auto import tqdm
import urllib

def find_zoom_level(latitudes, horizontal_coverage, horizontal_size):
    """Find the best matching zoom level for Google Maps Static API.

    Parameters
    ----------
    latitudes: pandas.Series, [n_places]
        list of latitudes for the centers of satellite images
    horizontal_coverage: int
        ideal horizontal length of the image coverage in km
    horizontal_size: int
        the horizontal length of the image in pixels; the maximum value is 640

    Returns
    -------
    zoom_levels: np.array, [n_places]
        list of best zoom levels for places
    actual_horizontal_coverage: list of str, [n_places]
        list of actual coverages of expected satellite images
    """
    # sort 'latitudes' from low to high with its original indices
    sorted_latitudes = sorted(zip(latitudes, range(len(latitudes))), key=lambda pair: pair[0])

    zoom_levels = np.zeros(len(latitudes))
    actual_horizontal_coverage = np.zeros(len(latitudes))

    best_zoom = 1
    for lat, index in sorted_latitudes:
        for zoom in range(best_zoom-1, 22):
            meter_per_pixel = 156543.03392 * np.cos(lat * np.pi / 180) / (2**zoom)
            horizontal_coverage_in_km = meter_per_pixel * np.array(horizontal_size) / 1000
            if horizontal_coverage_in_km > horizontal_coverage: # covered area is still too large
                prev_ratio = (horizontal_coverage_in_km / horizontal_coverage) ** 2
                prev_horizontal_coverage_in_km = horizontal_coverage_in_km
            else: # now covered area is too small
                ratio = (horizontal_coverage / horizontal_coverage_in_km) ** 2
                break
        if ratio <= prev_ratio: # a bit bigger coverage is closer to the ideal coverage
            zoom_levels[index] = zoom
            actual_horizontal_coverage[index] = horizontal_coverage_in_km
        else: # a bit smaller coverage is closer to the ideal coverage
            zoom_levels[index] = zoom - 1
            actual_horizontal_coverage[index] = prev_horizontal_coverage_in_km

    return zoom_levels.astype(int), actual_horizontal_coverage

def get_satellite_image(directory_name, API_key, IDs, latitude_longitude,
                        horizontal_coverage=2, horizontal_size=640,
                        image_ratio=1, image_scale=1, image_format="png",
                        n_jobs=1, verbose=True):
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
    horizontal_coverage: int, optional (default="2,2")
        ideal horizontal length of the image coverage in km
        saved images will NOT have the same exact dimensions but will have the closest possible dimensions
    horizontal_size: int, optional (default="640")
        the horizontal length of the image in pixels; the maximum value is 640
    image_ratio: float, optional (default=1)
        the ratio of the vertical length of the image to the horizontal length of the image
    image_scale: int, optional (default=1)
        scaling on the size
    image_format: str, optional (default="png")
        format of output images
    verbose: boolean, optional (default=True)
        whether or not to print the progress of the data retrieval
    """
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

    def get_single_sat_image(i):
        url = urls[i]
        file_name = directory_name + "/" + str(IDs[i]) + ".png"

        if os.path.exists(file_name):
            skip_id[i] = 1
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

    # find the best zoom levels to feed into Google Maps Static API and resulting side lengths of satellite images
    latitudes = latitude_longitude.apply(lambda x: x.split(",")[0]).astype(float)
    zoom_levels, actual_horizontal = find_zoom_level(latitudes=latitudes, horizontal_coverage=horizontal_coverage,
                                                horizontal_size=horizontal_size)

    # crate URLs
    prefix = "https://maps.googleapis.com/maps/api/staticmap?"
    center = "center=" + latitude_longitude
    zoom = "&zoom=" + pd.Series(zoom_levels, dtype=str)
    size = "&size=" + str(horizontal_size) + "x" + str(horizontal_size*image_ratio)
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
    if verbose: # with progress bar
        with tqdm_joblib(tqdm(desc='Data Retrieval Progress', total=len(IDs))) as progress_bar:
            Parallel(n_jobs) (delayed(get_single_sat_image)(i) for i in range(len(IDs)))
    else: # without progress bar
        Parallel(n_jobs) (delayed(get_single_sat_image)(i) for i in range(len(IDs)))

    # save actual side lengths of newly saved satellite images
    actual_horizontal_new = pd.Series(actual_horizontal[skip_id==0], dtype=str)
    actual_vertical_new = pd.Series(actual_horizontal_new * image_ratio, dtype=str)
    actual_coverage = actual_horizontal_new + 'x' + actual_vertical_new
    new_data = pd.DataFrame({'id': IDs[skip_id==0],
                                 'actual_coverage': actual_coverage})
    if csv_exist:
        with open(f"{directory_name}/image_coverage.csv", "a") as f:
            new_data.to_csv(f, index=False, header=False)

    else:
        with open(f"{directory_name}/image_coverage.csv", "w") as f:
            new_data.to_csv(f, index=False)

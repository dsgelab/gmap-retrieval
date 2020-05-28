import json
import numpy as np
import os
import pandas as pd
import time
import urllib

def use_nearby_search(url, next_page=False, request_count=0):
    """Call nearby search API request.

    Parameters
    ----------
    url: str
        URL to use to send a Nearby Search Request in Google Maps Place Search API
    next_page: boolean, optional(default=False)
        whether or not the URL is to request next page using next_page_token
    request_count: int, optional(default=0)
        the count of the previously-sent same requests; used only when next_page=True

    Returns
    -------
    data: dict
        returned API response
        check https://developers.google.com/places/web-service/search#find-place-responses for its structure
    status: str
        status of the API response
        check https://developers.google.com/places/web-service/search#PlaceSearchStatusCodes for details
    """
    while True:
        if next_page:
            time.sleep(3)
        try:
            # get API response
            print("API request made.")
            response = urllib.request.urlopen(url)
        except IOError:
            pass # retry
        else: # if no IOError occurs
            data = json.loads(response.read().decode('utf-8'))
            status = data['status']
            if status == "OK":
                break
            elif (status == "INVALID_REQUEST") & next_page: # if next_page_token is not valid yet
                if request_count >= 3:
                    print(f"Failed to receive a valid API response for 3 times for {url}.")
                    break # stop requesting after 3 trials
                else:
                    print("...Key is not valid yet.")
                    request_count += 1
                    data, status = use_nearby_search(url + "&request_count=" + str(request_count), next_page,
                                                     request_count)
                    break
            else:
                break
    return data, status

def concat_next_page(data, next_page):
    """Concatenate 'next_page' into 'data'.

    Parameters
    ----------
    data: dict
        a json file returned by Google Nearby Serch API in dict format
    next_page: dict
        a json file returned by Google Nearby Serch API in dict format
    """

    try:
        data["next_page_token"] = next_page["next_page_token"]
    except KeyError:
        del data["next_page_token"] # no 'next_page_token' key in 'next_page'

    # concat 'results'
    data['results'].extend(next_page["results"])

def get_nearby_places(directory_name, API_key, IDs, latitude_longitude, radius=1, place_types=None, verbose=True):
    """Get a list of places around specific locations specified by latitudes and longitudes using Google Maps Place Search API.

    Note that maximum number of properties you can obstain from this method
        for each [place, place type] pair (which are specified by [latitude_longitude, place_types]) pair is 60.
    This is due to the limitation of Google Maps Place Search API, check the details at:
        https://developers.google.com/places/web-service/search

    Paramters
    ---------
    directory_name: str
        name of a new directory containing all the saved images
    API_key: str
        key for Google Map API
    IDs: pandas Series [n_locations]
        list of IDs that identify locations
    latitude_longitude: pandas Series [n_locations]
        list of locations specified by latitude and longitude;
        each location needs to be comma-separated {latitude,longitude} pair; e.g."40.714728,-73.998672"
    radius: int, optional (default=1)
        raidus to search for places in km
    place_types: ndarray, optional (default=None)
        list of place types of Google Map to search for; if default, None, all the primary place types are searched
            Check https://developers.google.com/places/supported_types for further details
        Notice that this entry doesn't ensure that properties in collected data belong to a place type specified by this entry
            since this just specifies key words for search
            to make that sure, re-check the 'types' property in the collected json files
        Hence, alternatively, you can put a list of any key words here instead of place types of Google Map,
            then all properties matching with any of the key words are returned
    verbose: boolean, optional (default=True)
        whether or not to print the progress of the data retrieval
    """

    # a list of primary place types taken from https://developers.google.com/places/supported_types
    if place_types is None:
        place_types = ['accounting', 'airport', 'amusement_park', 'aquarium', 'art_gallery', 'atm', 'bakery', 'bank',
                       'bar', 'beauty_salon', 'bicycle_store', 'book_store', 'bowling_alley', 'bus_station', 'cafe',
                       'campground', 'car_dealer', 'car_rental', 'car_repair', 'car_wash', 'casino', 'cemetery', 'church',
                       'city_hall', 'clothing_store', 'convenience_store', 'courthouse', 'dentist', 'department_store',
                       'doctor', 'drugstore', 'electrician', 'electronics_store', 'embassy', 'fire_station', 'florist',
                       'funeral_home', 'furniture_store', 'gas_station', 'grocery_or_supermarket', 'gym', 'hair_care',
                       'hardware_store', 'hindu_temple', 'home_goods_store', 'hospital', 'insurance_agency',
                       'jewelry_store', 'laundry', 'lawyer', 'library', 'light_rail_station', 'liquor_store',
                       'local_government_office', 'locksmith', 'lodging', 'meal_delivery', 'meal_takeaway', 'mosque',
                       'movie_rental', 'movie_theater', 'moving_company', 'museum', 'night_club', 'painter', 'park',
                       'parking', 'pet_store', 'pharmacy', 'physiotherapist', 'plumber', 'police', 'post_office',
                       'primary_school', 'real_estate_agency', 'restaurant', 'roofing_contractor', 'rv_park', 'school',
                       'secondary_school', 'shoe_store', 'shopping_mall', 'spa', 'stadium', 'storage', 'store',
                       'subway_station', 'supermarket', 'synagogue', 'taxi_stand', 'tourist_attraction', 'train_station',
                       'transit_station', 'travel_agency', 'university', 'veterinary_care', 'zoo']

    elif type(place_types) is not list:
        raise TypeError("place_types must be a list.")

    # create URLs
    prefix = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
    locations = "location=" + latitude_longitude
    radius_meters = "&radius=" + str(radius*1000)
    keyword = "&keyword=" + pd.Series(place_types)
    key = "&key=" + API_key

    # create directory to put all the json files
    directory = directory_name
    if not os.path.exists(directory):
        os.mkdir(directory)

    # get info about properties around the locations specified by 'ID'
    for i in range(len(IDs)):
        ID = str(IDs[i])

        # create directory to put all json files about the location specified by 'ID'
        lower_dir = f"{ID}"
        if not os.path.exists(f"{directory}/{lower_dir}"):
            os.mkdir(f"{directory}/{lower_dir}")

        # 'urls' is an np.array, [n_place_types], that includes all URLs for a specific place, specified by 'ID'
        urls = prefix + locations[i] + radius_meters + keyword + key

        # loop through different types of propeties around the location specified by 'ID'
        for j in range(len(place_types)):
            url = urls[j]
            place_type = place_types[j]
            if os.path.exists(f"{directory}/{lower_dir}/{place_type}.json"):
                if verbose:
                    print(f"{directory}/{lower_dir}/{place_type}.json already exists.")
                continue

            #else
            data, status = use_nearby_search(url)

            while True:
                try:
                    # check if there's an additional list of properties
                    next_page_token = data['next_page_token']
                except KeyError:
                    break # no additional list
                else: # get the next page
                    if verbose:
                        print("...Get next page.")
                    pagetoken = "pagetoken=" + next_page_token
                    next_page_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json?" + pagetoken + key
                    next_page, next_page_status = use_nearby_search(next_page_url, next_page=True, request_count=0)
                    if next_page_status == 'OK':
                        concat_next_page(data, next_page)
                    else:
                        print(f"...There was a trouble in getting next page for {ID}-{place_type} ({next_page_status}).")

            # save into json file
            if status == 'OK':
                if verbose:
                    print(f"...Created {directory}/{lower_dir}/{place_type}.json")
                with open(f"{directory}/{lower_dir}/{place_type}.json", "w") as f:
                    json.dump(data, f)
            elif status == 'ZERO_RESULTS':
                if verbose:
                    print(f"...Created {directory}/{lower_dir}/{place_type}.json; No result for {ID}-{place_type}")
                with open(f"{directory}/{lower_dir}/{place_type}.json", "w") as f:
                    json.dump(data, f)
            else:
                print(f"The status of response is: {status} for {ID}-{place_type}.")
        if verbose:
            print(f"Finished retrieving data for {ID}\n")

def create_csv_nearby_places(directory_name, place_types, file_name=None):
    """Create data table from directory created by get_nearby_places function and save it into csv file.

    Parameters
    ----------
    directory_name: str
        name of directory containing sub-directories which have json files
    place_types: list
        list of place types to search for
    file_name: str, optional (default=None)
        name of csv file; if None, the file name becomes f"{directory_name}.csv"

    Returns
    -------
    df: pandas DataFrame or None
        structured data containing essential information in the json files
        if corresponding csv file exists, return None
    """
    if file_name==None:
        file_name = f"{directory_name}.csv"

    if os.path.exists(file_name):
        print(f"{file_name} already exists!")
        return pd.read_csv(file_name)

    IDs = []
    types = []
    name = []
    place_id = []
    price_level = []
    rating = []
    n_rating = []
    loc = []

    for ID in os.listdir(directory_name):
        for place_type in place_types:
            file_name = f"{directory_name}/{ID}/{place_type}.json"
            with open(file_name, 'r') as f:
                results = json.load(f)["results"]
            for i in range(len(results)):
                if place_type not in results[i]['types']:
                    continue
                IDs += [ID]
                types += [place_type]
                name += [results[i]['name']]
                place_id += [results[i]['place_id']]
                try:
                    price_level += [results[i]['price_level']]
                except KeyError:
                    price_level += [np.nan]
                try:
                    rating += [results[i]['rating']]
                except KeyError:
                    rating += [np.nan]
                try:
                    n_rating += [results[i]['user_ratings_total']]
                    if results[i]['user_ratings_total'] == 0:
                        rating[-1] = np.nan
                except KeyError:
                    n_rating += [np.nan]
                loc += [",".join([str(i) for i in results[i]['geometry']['location'].values()])]

    columns = ["id", "type", "name", "place_id", 'price_level', 'rating', 'n_rating', 'loc']

    df = pd.DataFrame({"id": IDs, "type": types, "name": name, "place_id": place_id, 'price_level': price_level,
                       'rating': rating, 'n_rating': n_rating, 'loc': loc})

    df.to_csv(f"{directory_name}.csv", header=True, index=False)

    return df

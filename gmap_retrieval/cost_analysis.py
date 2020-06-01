import glob
import json
import numpy as np
import os
import pandas as pd

def get_n_api_calls(n_loc, satellite, nearby_places, street_view, reviews, place_types=None):
    """Calculate how many API calls per location were made using methods in this package.

    Parameters
    ----------
    n_loc: int
        number of locations for which data were collected
    satellite: int or str
        if int, the number of satellite images retrieved for each location
        if str, a path to the directory created by get_satellite_image method
    nearby_places: str
        a path to the directory created by get_nearby_places method
    street_view: int or str
        if int, n_image variable used as input to 'get_street_view' method
        if str, a path to the directory created by get_street_view method
    reviews: str
        a path to the directory created by get_reviews method
    place_types: list
        'place_types' variable used as input to 'get_nearby_places' method

    Returns
    n_api_calls_per_loc: pandas.DataFrame
        expected number of calls of each API to be made to collect data per one location;
        can be used to run calculate_cost function as its input
    """
    # get the number of static map API requests made
    if type(satellite) is int:
        n_static_map = satellite
    elif type(satellite) is str:
        n_static_map = len(glob.glob1(satellite, "*.png"))/n_loc
    else:
        raise ValueError("satellite has to be either int or str.")

    # when place types are not specified
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

    # get the number of nearby search API requests made based on data
    count = np.zeros((n_loc, len(place_types)))
    for i, sub_dir in enumerate(os.listdir(nearby_places)):
        for j, p_type in enumerate(place_types):
            file_name = f"{nearby_places}/{sub_dir}/{p_type}.json"
            with open(file_name, "r") as f:
                count[i, j] = len(json.load(f)['results'])
    n_nearby_search = (np.ceil(count/20).sum().astype(int) + (count==0).sum())/n_loc

    # get the number of static street view API requests made
    if type(street_view) is int:
        n_street_view = street_view

    elif type(street_view) is str:
        counts = np.zeros(len(os.listdir(street_view)))
        for i, sub_dir in enumerate(os.listdir(street_view)):
            counts[i] = len(glob.glob1(f"{street_view}/{sub_dir}", "*.png"))
        n_street_view = counts.mean()
    else:
        raise ValueError("street_view has to be either int or str.")

    # get the number of places details API requests made based on data
    n_reviews = len(glob.glob1(reviews, "*.json"))/n_loc

    n_api_calls_per_loc = pd.Series([n_static_map, n_nearby_search, n_street_view, n_reviews],
                                    index=['static_maps', 'nearby_search', 'static_street_view', 'places_details(atmosphere)'])

    return n_api_calls_per_loc

def calculate_cost(n_loc, price_table, n_api_calls_per_loc, extra_expense=0):
    """Calculate and print expected cost incurred when retrieving data using Google API for a list of locations.

    If using the default pricing table by setting 'price_table'=None, check if the default pricing table below matches
        the official pricing table published by Google (https://cloud.google.com/maps-platform/pricing/sheet)

    ----- Default Pricing Table: Updated on May 3, 2020
    Cost for Maps Static API: $2 per 1000 requests up to 100,000; $1.6 per 1000 requests up to 500,000
    Cost for Places API Nearby Search request: $40 per 1000 requests up to 100,000; $32 per 1000 requests up to 500,000
    Cost for Street View Static API: $7 per 1000 requests up to 100,000; $5.6 per 1,000 requests up to 500,000
    Cost for Street View Static API metadata request: free (unlimited)
    Cost for Place Details API (with atmosphere data): $22 per 1000 requests up to 100,000; $17.6 per 1,000 requests up to 500,000
    -----

    Also, note that the data retrieval is asuumed to start and end within a single month
    If it spans for more than one month, the cost can be much more expensive than the estimate

    Parameters
    ----------
    n_loc: int
        number of locations to retrieve data of
    price_table: pandas.DataFrame, shape [n_API, n_price_range]; or None
        pricing table to use; if None, the default pricing table is used.
        DataFrame's index is the type of API.
        The columns are the list of integers which indicate
            the threshoulds of API calls between the price ranges.
        The elements of DataFrame have to be the API price per 1000 calls in USD for corresponding API and price range
        For example, the default pricing table is constructed as below:
            price_table = {'static_maps': [2, 1.6], 'nearby_search': [40, 32], 'static_street_view': [7, 5.6],
                           'places_details': [22, 17.6]}
            price_table = pd.DataFrame(price_table.values(), index=price_table.keys(), columns=[0, 100000])
    n_api_calls_per_loc: pandas.Series, shape [n_API]
        expected number of calls of each API to be made to collect data per one location
        index must be identical the index of price_table
        if you set 'price_table'=None, index of n_api_calls need to be:
            ['static_maps', 'nearby_search', 'static_street_view', 'places_details(atmosphere)']
    extra_expense: float, optional (default: 0)
        extra expense (or expense waiver) regardless of the amount of API calls
        For example, you can put -200 in order to account the 200 discount you get every month from Google
    """
    if price_table is None: # if default pricing table is used
        price_table = {'static_maps': [2, 1.6], 'nearby_search': [40, 32], 'static_street_view': [7, 5.6],
                       'places_details(atmosphere)': [22, 17.6]}
        price_table = pd.DataFrame(price_table.values(), index=price_table.keys(), columns=[0, 100000])

    # check input is appropriate
    if set(n_api_calls_per_loc.index)!=set(price_table.index):
        raise ValueError("Indices of n_api_calls_per_loc and price_table have to be identical.")

    n_api_calls=n_api_calls_per_loc*n_loc

    prices = dict()
    for index, row in price_table.iterrows():
        n_calls_by_range = np.maximum(n_api_calls[index]-price_table.columns.values, 0)
        for i in range(len(n_calls_by_range)-1):
            n_calls_by_range[i] -= n_calls_by_range[i+1]
        prices[index] = np.sum(n_calls_by_range*(price_table.loc[index]/1000))

    total = sum(prices.values()) + extra_expense

    print(f"The total cost for {n_loc} entries is: {total} USD (avg={total/n_loc}).")

    for index in prices:
        if prices[index]!=0:
            print(f"   {index} cost {prices[index]} USD (avg={prices[index]/n_loc}).")

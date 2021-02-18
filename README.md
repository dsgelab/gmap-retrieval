# gmap_retrieval (Unstable Version: No Test Available)

## Overview
This Python package is for retrieving geographical data using Google API based on a list of locations specified by latitudes and longitudes.　

Using this package, you can fetch:
* satellite images centered around the input locations,
* Google street view images from randomly-chosen locations around the input locations, and
* various data on Google Maps about properties around the input locations such as the number of restaurants and average price level of properties.

You can also:
* get list of user reviews based on a list of [Google Place IDs](https://developers.google.com/places/place-id) of properties of interests, and
* predict the cost when collecting different types of data using above functions.

This package was developed for the purpose of collecting geographical data of individuals in biobank datasets in research contexts.  

## Examples
```
from gmap_retrieval import *
import pandas as pd

# key is your own Google API key
key='Your API key'
output_dir = "save_"

data = pd.DataFrame([[1, '40.752937,-73.977240', 'NYC Grand Central Station'],
                     [2, '51.531090,-0.125752', 'London St Pancras Station'],
                     [3, '35.681463,139.767157', 'Tokyo Station'],
                     [4, '48.844544,2.374431', 'Paris-Gare-de-Lyon'],
                     [5, '60.171283,24.941472', 'Helsinki Central Station']],
                    columns=['id', 'loc', 'place'])

# get satellite images for locations in the 'data' variable
# this will store satellite images in the directory "satellite_images"
get_satellite_image(directory_name=f"{output_dir}/satellite_images",
                    API_key=key, IDs=data['id'], latitude_longitude=data['loc'],
                    n_jobs=-1)

# get street view images from areas around the locations in the 'data' variable
# this will store street view images in the directory "street_views"
get_street_view_image(directory_name=f'{output_dir}/street_view', API_key=key,
                      IDs=data['id'], latitude_longitude=data['loc'],
                      n_images=10, search_radius=100, n_jobs=-1)

# get data of nearby restaurants on Google Maps
# around the locations in the 'data' variables
# this function saves json files containing data about nearby restaurants
# under the directory called 'nearby_places'
get_nearby_places(directory_name='nearby_places', API_key=key,
                  IDs=data['id'], latitude_longitude=data['loc'],
                  radius=1, place_types=['restaurant'],
                  verbose=True)

# create csv file called 'nearby_places.csv' from json files
# under the directory 'nearby_places'
nearby_places = create_csv_nearby_places(directory_name='nearby_places',
                                         place_types=['restaurant'],
                                         file_name=None)

place_id = nearby_places['place_id']

# get reviews for the restaurants around the locations in the 'data' variables
# saves json files containing review data under directory called 'reviews'
get_reviews(directory_name='reviews', API_key=key, place_id=place_id,
            verbose=True)

# create csv file called 'reviews.csv' from json files
# under the directory 'reviews'
_ = create_csv_reviews(directory_name='reviews', file_name=None)

# get the number of API calls made per location
n_api_calls_per_loc = get_n_api_calls(n_loc=len(data),
                                      satellite='satellite_images',
                                      nearby_places='nearby_places',
                                      street_view='street_view',
                                      reviews='reviews',
                                      place_types=['restaurant'])

# predict the cost for further data collection of 1000 locations
# nearby_search_per_entry and n_reviews_per_entry need to be estimated,
# but estimate based on only 5 examples as done above
# would not be reliable in practice
calculate_cost(n_loc=1000, price_table=None, # use default price table
               n_api_calls_per_loc=n_api_calls_per_loc,
               extra_expense=0)
```


## Requirements
* [Get your own Google API key](https://developers.google.com/places/web-service/get-api-key).
* numpy 1.18.1
* pandas 1.0.1
* tqdm 4.43
* joblib 0.14.1

## Disclaimer
This package is built based on Google APIs, and any change in the APIs might cause problems in running this package.  
Especially, when using the method calculate_cost, please check if [the official pricing table](https://cloud.google.com/maps-platform/pricing/sheet) is reflected in the price table in the docstring of the method.

## Documentation
Check docstrings of methods for details.

## Installation
`pip install git+https://github.com/dsgelab/gmap_retrieval.git`

## Author
* Takao Shimizu  
* tshimizu.midd@gmail.com

## License
gmap_retrieval is under [BSD 3-Clause License](https://en.wikipedia.org/wiki/BSD_licenses#3-clause_license_(%22BSD_License_2.0%22,_%22Revised_BSD_License%22,_%22New_BSD_License%22,_or_%22Modified_BSD_License%22)).

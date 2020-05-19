# gmap_retrieval

## Overview
This Python package is for retrieving geographical data from Google API based on a list of locations specified by latitudes and longitudes.　

Using this package, you can fetch:
1. satellite images centered around the input locations,
2. Google street view images from areas around the input locations, and
3. various data on Google Maps about properties around the input locations.

You can also:
4. get list of user reviews based on a list of [Google Place IDs](https://developers.google.com/places/place-id) of properties of interests, and
5. predict the cost when collecting different types of data using this package.

This package was originally developed for the purpose of collecting geographical data of individuals in biobank datasets in research contexts.  

## Examples
```
from gmap_retrieval import *
import pandas as pd

# key is your own Google API key
key='Your API key'

data = pd.DataFrame([[1, '40.752937,-73.977240', 'NYC Grand Central Station'],
                     [2, '51.531090,-0.125752', 'London St Pancras Station'],
                     [3, '35.681463,139.767157', 'Tokyo Station'],
                     [4, '48.844544,2.374431', 'Paris-Gare-de-Lyon'],
                     [5, '60.171283,24.941472', 'Helsinki Central Station']],
                    columns=['id', 'loc', 'place'])

# get satellite images for locations in the 'data' variable
# this will store satellite images in the directory "satellite_images"
get_satellite_image(directory_name="satellite_images", API_key=key,
                    IDs=data['id'], latitude_longitude=data['loc'],
                    side_length=2, image_size="640x640", image_scale=1,
                    image_format="png")

# get street view images from areas around the locations in the 'data' variable
# this will store street view images in the directory "street_views"
get_street_view_image(directory_name='street_view', API_key=key,
                      IDs=data['id'], latitude_longitude=data['loc'],
                      n_images=10, rad=1, camera_direction=-1,
                      field_of_view=120, angle=0, search_radius=100,
                      image_type="outdoor", image_size="640x640")

# get data of nearby restaurants on Google Maps
# around the locations in the 'data' variables
# this function saves json files containing data about nearby restaurants
# under the directory called 'nearby_places'
get_nearby_places(directory_name='nearby_places', API_key=key,
                  IDs=data['id'], latitude_longitude=data['loc'],
                  radius=1, place_types=['restaurant'])

# create csv file called 'nearby_places.csv' from json files
# under the directory 'nearby_places'
nearby_places = create_csv_nearby_places(directory_name='nearby_places',
                                         place_types='restaurant',
                                         file_name=None)

place_id = nearby_places['place_id']

# get reviews for the restaurants around the locations in the 'data' variables
# saves json files containing review data under directory called 'reviews'
get_reviews(directory_name='reviews', API_key=key, place_id=place_id)

# create csv file called 'reviews.csv' from json files
# under the directory 'reviews'
_ = create_csv_reviews(directory='reviews', file_name=None)

# get the number of API calls made per location
n_API_calls_per_loc = get_n_api_calls(n_loc=len(data),
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
               n_API_calls_per_loc=n_API_calls_per_loc,
               extra_expense=0)
```


## Requirements
* [Get your own Google API key](https://developers.google.com/places/web-service/get-api-key).
* numpy 1.18.1
* pandas 1.0.1

## Disclaimer
This package is built based on Google APIs, and any change in the APIs might cause problems in running this package.  
Especially, when using the method calculate_cost, please check if [the official pricing table](https://cloud.google.com/maps-platform/pricing/sheet) is reflected in the price table in the docstring of the method.

## Documentation
Check docstrings of methods for details.

## Installation
`pip install git+https://github.com/TShim/gmap_retrieval.git`

## Author
* Takao Shimizu  
* tshimizu.midd@gmail.com

## License
gmap_retrieval is under [MIT License](https://en.wikipedia.org/wiki/MIT_License).
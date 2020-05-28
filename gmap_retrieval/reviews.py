import json
import os
import pandas as pd
import urllib

def get_reviews(directory_name, API_key, place_id, verbose=True):
    """Retrieve and save reviews of properties through Google Map Places Details API as json files.

    Parameters
    ----------
    directory_name: str
        name of a new directory containing all the saved json files
    API_key: str
        key for Google Map API
    place_id: list
        list of place IDs of Google Map of which the method get reviews
    verbose: boolean, optional (default=True)
        whether or not to print the progress of the data retrieval
    """
    if not os.path.exists(directory_name):
        os.mkdir(directory_name)

    prefix = "https://maps.googleapis.com/maps/api/place/details/json?"
    place_id_ = "place_id=" + pd.Series(place_id)
    fields = "&fields=name,place_id,type,review"
    key = "&key=" + API_key

    urls = prefix + place_id_ + fields + key

    for i in range(len(place_id_)):
        url = urls[i]

        if os.path.exists(f"{directory_name}/{place_id[i]}.json"):
            if verbose:
                print(f"{directory_name}/{place_id[i]}.json already exists.")
            continue

        while True:
            try:
                # get API response
                if verbose:
                    print("API request made.")
                response = urllib.request.urlopen(url)
            except IOError:
                pass # retry
            else: # if no IOError occurs
                data = json.loads(response.read().decode('utf-8'))
                if verbose:
                    print(f"...Created {directory_name}/{place_id[i]}.json")
                with open(f"{directory_name}/{place_id[i]}.json", "w") as f:
                    json.dump(data, f)
                break

def create_csv_reviews(directory_name, file_name=None):
    """Create data table from directory created by get_reviews function and save it into csv file.

    Parameters
    ----------
    directory_name: str
        name of directory containing json files
    file_name: str, optional (default=None)
        name of csv file; if None, the file name becomes f"{directory_name}.csv"

    Returns
    df: pandas DataFrame or None
        structured data containing essential information in the json files
        if if corresponding csv file exists, return None
    """
    if file_name==None:
        file_name = f"{directory_name}.csv"

    if os.path.exists(file_name):
        print(f"{file_name} already exists!")
        return None

    place_id = []
    place_name = []
    review_text = []
    review_rating = []
    review_time = []
    review_language = []

    for place_json in os.listdir(directory_name):
        if place_json.startswith("."):
            continue
        file_name = f"{directory_name}/{place_json}"
        with open(file_name, 'r') as f:
            results = json.load(f)["result"]

        try:
            for review in results["reviews"]:
                place_id += [results["place_id"]]
                place_name += [results["name"]]
                review_text += [review["text"]]
                review_rating += [review["rating"]]
                review_time += [review["time"]]
                try:
                    review_language += [review["language"]]
                except KeyError:
                    review_language += ["na"]
        except KeyError:
            continue

    columns = ["place_id", "place_name", "review_text", "review_rating", 'review_time', 'review_language']

    df = pd.DataFrame({"place_id": place_id, "place_name": place_name, "review_text": review_text,
                       "review_rating": review_rating, 'review_time': review_time, 'review_language': review_language})

    df.to_csv(f"{directory_name}.csv", header=True, index=False)

    return df

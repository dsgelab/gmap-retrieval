import unittest
from gmap_retrieval.cost_analysis import calculate_cost
import pandas as pd


class CostAnalysisTest(unittest.TestCase):
    def setUp(self):
        price_table = {'static_maps': [2, 1.6], 'nearby_search': [40, 32],
                       'static_street_view': [7, 5.6],
                       'places_details(atmosphere)': [22, 17.6]}
        self.price_table = pd.DataFrame(price_table.values(),
                                        index=price_table.keys(),
                                        columns=[0, 100000])

    def tearDown(self):
        pass

    def testCalcCost(self):
        api_counts1 = pd.Series([5000, 5000, 5000, 5000],
                                index=['static_maps',
                                       'nearby_search',
                                       'static_street_view',
                                       'places_details(atmosphere)'])
        cost1 = pd.Series([355, 10, 200, 35, 110],
                          index=['total',
                                 'static_maps',
                                 'nearby_search',
                                 'static_street_view',
                                 'places_details(atmosphere)'])
        result1 = calculate_cost(1, self.price_table, api_counts1,
                                 extra_expense=0)
        api_counts2 = pd.Series([200000, 200000, 200000, 200000],
                                index=['static_maps',
                                       'nearby_search',
                                       'static_street_view',
                                       'places_details(atmosphere)'])
        cost2 = pd.Series([12880, 360, 7200, 1260, 3960],
                          index=['total',
                                 'static_maps',
                                 'nearby_search',
                                 'static_street_view',
                                 'places_details(atmosphere)'])
        result2 = calculate_cost(1, self.price_table, api_counts2,
                                 extra_expense=100)
        for idx in result1.index:
            self.assertEqual(result1[idx], cost1[idx])
        for idx in result2.index:
            self.assertEqual(result2[idx], cost2[idx])

    def testGetNAPICalls(self):
        return


if __name__ == "__main__":
    unittest.main()

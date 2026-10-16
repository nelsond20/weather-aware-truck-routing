import unittest
from copy import deepcopy
from routing.domain.models import Coordinate
from routing.providers.base import ProviderError
from routing.providers.photon import PhotonGeocodingProvider

PAYLOAD={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Point','coordinates':[-100,40]},'properties':{'osm_type':'N','osm_id':123,'name':'Example town','state':'Region','country':'US'}}]}

class PhotonTests(unittest.TestCase):
    def test_normalized_candidates_and_credential_free_query(self):
        calls=[]
        def request(url,params):calls.append((url,params));return deepcopy(PAYLOAD)
        candidate=PhotonGeocodingProvider(request).search(' Example ')[0]
        self.assertEqual(candidate.coordinate,Coordinate(-100,40))
        self.assertEqual(candidate.label,'Example town, Region, US')
        self.assertEqual(candidate.candidate_id,'photon:N:123')
        self.assertEqual(calls,[('https://photon.komoot.io/api/',{'q':'Example','limit':'5','lang':'en'})])

    def test_address_without_name_and_duplicate_ids(self):
        payload=deepcopy(PAYLOAD)
        payload['features'][0]['properties']={'osm_type':'W','osm_id':456,'housenumber':'10','street':'Main Street','city':'Town','state':'Town','country':'US'}
        payload['features']*=2
        candidates=PhotonGeocodingProvider(lambda *args:payload).search('Main Street')
        self.assertEqual(len(candidates),1)
        self.assertEqual(candidates[0].label,'10 Main Street, Town, US')

    def test_empty_results_are_valid(self):
        self.assertEqual(PhotonGeocodingProvider(lambda *args:{'type':'FeatureCollection','features':[]}).search('Nowhere'),())

    def test_invalid_feature_rejected(self):
        for field,value in (('osm_type','X'),('osm_id',True),('name',42)):
            payload=deepcopy(PAYLOAD);payload['features'][0]['properties'][field]=value
            with self.subTest(field=field),self.assertRaises(ProviderError):
                PhotonGeocodingProvider(lambda *args:payload).search('Example')
        payload=deepcopy(PAYLOAD);payload['features'][0]['geometry']['coordinates']=[0,91]
        with self.assertRaises(ProviderError):PhotonGeocodingProvider(lambda *args:payload).search('Example')

    def test_invalid_query_does_not_call_transport(self):
        def unexpected(*args):raise AssertionError('transport called')
        for query in ('  ','x','a;b','a'*201):
            with self.subTest(query=query),self.assertRaises(ValueError):PhotonGeocodingProvider(unexpected).search(query)

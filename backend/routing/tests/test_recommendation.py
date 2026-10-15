import unittest
from datetime import datetime,timedelta,timezone
from routing.domain.models import Coordinate,RawRoute,RouteSegment,Checkpoint,WeatherObservation,RiskLevel
from routing.domain.recommendation import evaluate_route,recommend_routes

NOW=datetime(2026,10,13,12,tzinfo=timezone.utc)
def fixture(route_id,distances=(10,5),winds=(20,20,20),duration=18000,missing=False):
    coords=tuple(Coordinate(-100+i*.1,40) for i in range(len(distances)+1))
    segments=tuple(RouteSegment(coords[i],coords[i+1],miles*1609.344,duration*miles/sum(distances)) for i,miles in enumerate(distances))
    raw=RawRoute(route_id,coords,segments)
    points=[Checkpoint(coords[0],0,NOW)]
    distance=seconds=0
    for segment in segments:
        distance+=segment.distance_m
        seconds+=segment.duration_s
        points.append(Checkpoint(segment.end,distance,NOW+timedelta(seconds=seconds)))
    observations=tuple(WeatherObservation(wind,None if missing else 0,0,p.eta,p.eta-timedelta(hours=1),p.eta) for wind,p in zip(winds,points))
    return evaluate_route(raw,tuple(points),observations,0)

class RecommendationTests(unittest.TestCase):
    def test_severe_miles_beat_shorter_travel_and_blocked_is_excluded(self):
        safe=fixture('safe')
        severe=fixture('severe',(1,1),(20,45,20),14400)
        blocked=fixture('blocked',(1,1),(20,55,20),10800)
        result=recommend_routes((safe,severe,blocked))
        self.assertEqual(result.route_id,'safe')
        self.assertEqual(result.ranked_route_ids,('safe','severe'))
        self.assertEqual(result.deciding_criterion,'severe_miles')
        self.assertEqual(result.comparison_criteria,{'severe':'severe_miles','blocked':'blocked'})

    def test_high_miles_precede_average_and_time(self):
        moderate=fixture('moderate',(25,),(25,25),20000)
        high=fixture('high',(1,),(35,35),100)
        result=recommend_routes((moderate,high))
        self.assertEqual(result.route_id,'moderate')
        self.assertEqual(result.deciding_criterion,'high_miles')

    def test_average_precedes_time(self):
        low=fixture('low',(100,),(0,0),20000)
        moderate=fixture('moderate',(1,),(25,25),100)
        result=recommend_routes((low,moderate))
        self.assertEqual(result.route_id,'low')
        self.assertEqual(result.deciding_criterion,'average_risk')

    def test_time_then_stable_id_breaks_ties(self):
        result=recommend_routes((fixture('slow',duration=20000),fixture('fast',duration=10000)))
        self.assertEqual(result.route_id,'fast')
        self.assertEqual(result.deciding_criterion,'duration_seconds')
        result=recommend_routes((fixture('z'),fixture('a')))
        self.assertEqual(result.route_id,'a')
        self.assertEqual(result.deciding_criterion,'stable_tie')

    def test_exposure_is_distance_weighted_and_conserved(self):
        route=fixture('r',(10,5),(25,25,35))
        self.assertAlmostEqual(route.miles_by_level[RiskLevel.MODERATE],10)
        self.assertAlmostEqual(route.miles_by_level[RiskLevel.HIGH],5)
        self.assertAlmostEqual(route.average_risk,4/3)
        self.assertAlmostEqual(sum(route.miles_by_level.values()),15)

    def test_unknown_and_known_block_preserved(self):
        route=fixture('blocked',(10,5),(20,20,55),missing=True)
        self.assertTrue(route.blocked)
        self.assertFalse(route.complete)
        self.assertAlmostEqual(route.unknown_miles,15)
        self.assertIsNone(route.average_risk)
        self.assertEqual(recommend_routes((route,)).status,'all_blocked')

    def test_origin_and_destination_block_the_route(self):
        for winds in ((55,20,20),(20,20,55)):
            with self.subTest(winds=winds):self.assertTrue(fixture('r',winds=winds).blocked)

    def test_incomplete_route_is_not_recommended(self):
        unknown=fixture('unknown',missing=True)
        self.assertEqual(recommend_routes((unknown,)).status,'insufficient_data')
        self.assertIsNone(recommend_routes((unknown,)).route_id)
        self.assertEqual(recommend_routes((unknown,fixture('safe'))).comparison_criteria,{'unknown':'incomplete'})
        self.assertEqual(recommend_routes(()).status,'no_routes')

    def test_single_eligible_route_and_invalid_sampling(self):
        evaluated=fixture('safe')
        self.assertEqual(recommend_routes((evaluated,)).deciding_criterion,'only_eligible_route')
        with self.assertRaises(ValueError):
            evaluate_route(evaluated.route,evaluated.checkpoints,evaluated.observations[:-1],0)
        with self.assertRaises(ValueError):
            evaluate_route(evaluated.route,evaluated.checkpoints[:-1],evaluated.observations[:-1],0)

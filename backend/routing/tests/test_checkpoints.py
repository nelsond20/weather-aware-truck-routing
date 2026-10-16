import unittest
from datetime import datetime, timedelta, timezone
from routing.domain.models import Coordinate, RawRoute, RouteSegment
from routing.domain.checkpoints import sample_route, clip_route_geometry
from routing.domain.geometry import haversine_m, interpolate_coordinate

UTC=datetime(2026,10,13,12,tzinfo=timezone.utc)
A,B,C=Coordinate(-100,40),Coordinate(-99.5,40),Coordinate(-99,40)

def route():
    return RawRoute('r1',(A,B,C),(RouteSegment(A,B,16093.44,600),RouteSegment(B,C,8046.72,900)))

class CheckpointTests(unittest.TestCase):
    def test_segment_times_and_partial_final_interval(self):
        points=sample_route(route(),UTC,10)
        self.assertEqual([round(p.distance_m/1609.344,6) for p in points],[0,10,15])
        self.assertEqual(points[1].eta,UTC+timedelta(seconds=600))
        self.assertEqual(points[-1].eta,UTC+timedelta(seconds=1500))
        self.assertEqual(points[-1].coordinate,C)

    def test_routes_shorter_than_spacing_have_origin_and_destination(self):
        for spacing in (25,50):
            with self.subTest(spacing=spacing):
                self.assertEqual(len(sample_route(route(),UTC,spacing)),2)

    def test_exact_multiple_does_not_duplicate_destination(self):
        raw=RawRoute('r',(A,B),(RouteSegment(A,B,16093.44,600),))
        self.assertEqual(len(sample_route(raw,UTC,10)),2)

    def test_trailing_zero_distance_keeps_all_time(self):
        raw=RawRoute('r',(A,B,B),(RouteSegment(A,B,16093.44,600),RouteSegment(B,B,0,90)))
        points=sample_route(raw,UTC,10)
        self.assertEqual(len(points),2)
        self.assertEqual(points[0].eta,UTC)
        self.assertEqual(points[-1].eta,UTC+timedelta(seconds=690))

    def test_leading_zero_distance_contributes_to_later_eta(self):
        raw=RawRoute('r',(A,A,B),(RouteSegment(A,A,0,90),RouteSegment(A,B,16093.44,600)))
        self.assertEqual(sample_route(raw,UTC,10)[-1].eta,UTC+timedelta(seconds=690))

    def test_offset_is_normalized_to_utc(self):
        offset=UTC.astimezone(timezone(timedelta(hours=-5)))
        self.assertEqual(sample_route(route(),offset,10),sample_route(route(),UTC,10))

    def test_invalid_inputs_are_rejected(self):
        for depart,spacing in ((UTC.replace(tzinfo=None),10),(UTC,0),(UTC,15),(UTC,True)):
            with self.subTest(spacing=spacing),self.assertRaises(ValueError):
                sample_route(route(),depart,spacing)
        for distance,duration in ((-1,10),(0,10),(float('nan'),10),(10,-1),(10,float('inf'))):
            raw=RawRoute('r',(A,B),(RouteSegment(A,B,distance,duration),))
            with self.subTest(distance=distance),self.assertRaises(ValueError):
                sample_route(raw,UTC,10)
        bad=RawRoute('r',(A,B,C),(RouteSegment(A,C,10,10),))
        with self.assertRaises(ValueError):sample_route(bad,UTC,10)

    def test_dateline_uses_short_arc(self):
        west,east=Coordinate(179.9,0),Coordinate(-179.9,0)
        midpoint=interpolate_coordinate(west,east,.5)
        self.assertGreater(abs(midpoint.longitude),179)
        self.assertAlmostEqual(midpoint.latitude,0)
        self.assertAlmostEqual(haversine_m(west,east),22239.016,places=2)

    def test_clipping_retains_road_bend(self):
        raw=RawRoute('r',(Coordinate(0,0),Coordinate(1,0),Coordinate(1,1)),(
            RouteSegment(Coordinate(0,0),Coordinate(1,0),100,10),
            RouteSegment(Coordinate(1,0),Coordinate(1,1),100,10)))
        clipped=clip_route_geometry(raw,50,150)
        self.assertEqual(len(clipped),3)
        self.assertEqual(clipped[1],Coordinate(1,0))
        self.assertAlmostEqual(clipped[0].longitude,.5)
        self.assertAlmostEqual(clipped[-1].latitude,.5)
        with self.assertRaises(ValueError):clip_route_geometry(raw,-1,150)

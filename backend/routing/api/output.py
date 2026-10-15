from routing.domain.checkpoints import clip_route_geometry
from routing.domain.geometry import MILE_M

def iso(value):return value.isoformat().replace('+00:00','Z') if value is not None else None

def level(value):return value.name.lower() if value is not None else None

def geometry(points):return {'type':'LineString','coordinates':[[p.longitude,p.latitude] for p in points]}

def trip_json(evaluation,request,mode,request_id):
    routes = []
    for result in evaluation.routes:
        route = result.route
        checkpoints = []
        for cp,obs,risk in zip(result.checkpoints,result.observations,result.risks):
            checkpoints.append({'coordinate':[cp.coordinate.longitude,cp.coordinate.latitude],'distance_miles':cp.distance_m/MILE_M,'eta':iso(cp.eta),
                'level':level(risk.level),'known_max':level(risk.known_max),'wind_level':level(risk.wind_level),'rain_level':level(risk.rain_level),'snow_level':level(risk.snow_level),
                'wind_mph':obs.wind_mph,'rain_in_hr':obs.rain_in_hr,'snow_in_hr':obs.snow_in_hr,'wind_valid_at':iso(obs.wind_valid_at),
                'accumulation_start':iso(obs.accumulation_start),'accumulation_end':iso(obs.accumulation_end),'missing_fields':list(risk.missing_fields),'reasons':list(risk.reasons)})
        intervals = [{'start_index':i,'end_index':i+1,'distance_miles':(iv.end.distance_m-iv.start.distance_m)/MILE_M,'level':level(iv.level),
                     'geometry':geometry(clip_route_geometry(route,iv.start.distance_m,iv.end.distance_m))} for i,iv in enumerate(result.intervals)]
        routes.append({'route_id':route.route_id,'geometry':geometry(route.geometry),'distance_miles':result.checkpoints[-1].distance_m/MILE_M,
            'duration_seconds':sum(s.duration_s for s in route.segments),'arrival_at':iso(result.checkpoints[-1].eta),'eta_approximate':route.eta_approximate,
            'blocked':result.blocked,'complete':result.complete,'miles_by_level':{level(k):v for k,v in result.miles_by_level.items()},
            'unknown_miles':result.unknown_miles,'average_risk':result.average_risk,'checkpoints':checkpoints,'intervals':intervals})
    recommendation = evaluation.recommendation
    return {'mode':mode,'request_id':request_id,'departure_at':iso(request.departure_at),'load_lb':request.load_lb,'spacing_miles':request.spacing_miles,
        'warnings':list(evaluation.warnings),'recommendation':{'route_id':recommendation.route_id,'status':recommendation.status,'ranked_route_ids':list(recommendation.ranked_route_ids),
        'deciding_criterion':recommendation.deciding_criterion,'comparison_criteria':recommendation.comparison_criteria},'routes':routes}

def corridor_json(result,mode):
    locations=result.grid.locations
    frames=[]
    for frame in result.frames:
        known=sum(r.level is not None for r in frame.risks)
        frames.append({'valid_at':iso(frame.valid_at),'levels':[level(r.level) for r in frame.risks],
                       'known_max':[level(r.known_max) for r in frame.risks],'coverage':{'known_samples':known,'total_samples':len(locations)}})
    return {'base_time':iso(result.base_time),'width_miles':result.grid.width_miles,'resolution_m':result.grid.resolution_m,
        'locations':[[p.longitude,p.latitude] for p in locations],'frames':frames,'mode':mode,
        'coverage':{'known_samples':sum(f['coverage']['known_samples'] for f in frames),'total_samples':len(locations)*len(frames)}}

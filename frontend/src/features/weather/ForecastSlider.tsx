import { useId } from 'react';
import type { CorridorResponse,Coverage } from '../../api/types';
import styles from './ForecastSlider.module.css';
type Props={frames:CorridorResponse['frames'];selectedFrame:number;onSelectFrame:(index:number)=>void;coverage:Coverage;baseTime:string};
export function ForecastSlider({frames,selectedFrame,onSelectFrame,coverage,baseTime}:Props){
  const id=useId();const frame=frames[selectedFrame];
  return <section className={styles.panel} aria-label="Corridor forecast"><h2>48-hour corridor forecast</h2>
    <label htmlFor={id}>Forecast hour</label><input id={id} type="range" min="0" max="48" step="1" value={selectedFrame} aria-valuetext={frame?new Date(frame.valid_at).toISOString():'Unknown hour'} onChange={event=>onSelectFrame(Number(event.target.value))}/>
    <div className={styles.ticks} aria-hidden="true"><span>Now</span><span>12 h</span><span>24 h</span><span>36 h</span><span>48 h</span></div>
    <p aria-live="polite"><strong>{frame?new Date(frame.valid_at).toISOString().replace('T',' ').replace('.000Z',' UTC'):'Outside coverage'}</strong> · {coverage.known_samples}/{coverage.total_samples} known samples</p>
    {coverage.known_samples<coverage.total_samples&&<p>Coverage incomplete: unknown samples are not Low risk.</p>}
    <p className={styles.hint}>Window starts {baseTime}. Weather risk depends on truck load; this view does not change the arrival-based recommendation.</p>
  </section>;
}

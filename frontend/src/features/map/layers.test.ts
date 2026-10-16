import { it,expect,vi } from 'vitest';
import type { LayerMapPort,GeoJsonSourcePort } from './mapAdapter';
import { installTripLayers,updateTripLayers } from './layers';
import { sampleTrip } from '../../test/fixtures';
it('updates sources without recreating the five trip layers',()=>{
  const registry=new Map<string,GeoJsonSourcePort>();
  const fake:LayerMapPort={getSource:vi.fn(id=>registry.get(id)),addSource:vi.fn((id:string)=>registry.set(id,{setData:vi.fn()})),addLayer:vi.fn(),setFilter:vi.fn(),setPaintProperty:vi.fn()};
  const palette={low:'green',moderate:'gold',high:'orange',severe:'red',no_travel:'purple',unknown:'gray'};
  installTripLayers(fake,palette);updateTripLayers(fake,sampleTrip.routes,'r1');updateTripLayers(fake,sampleTrip.routes,'r1');
  expect(fake.addLayer).toHaveBeenCalledTimes(5);expect(registry.get('trip-intervals')?.setData).toHaveBeenCalledTimes(2);
});

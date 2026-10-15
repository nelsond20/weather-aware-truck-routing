import type { Meta,StoryObj } from '@storybook/react-vite';
import { expect,fn,userEvent } from 'storybook/test';
import { TripMap } from './TripMap';
import { sampleTrip } from '../../test/fixtures';
const meta={component:TripMap,args:{routes:sampleTrip.routes,selectedRouteId:sampleTrip.routes[0]?.route_id??null,onSelectRoute:fn(),heatmapFrame:null}} satisfies Meta<typeof TripMap>;
export default meta;type Story=StoryObj<typeof meta>;
export const Inspect:Story={play:async({canvas})=>{
  const button=canvas.getByRole('button',{name:/Checkpoint 1 ·/});button.focus();await userEvent.keyboard('{Enter}');
  await expect(canvas.getByRole('status')).toHaveTextContent('Wind');
}};
export const Empty:Story={args:{routes:[],selectedRouteId:null}};

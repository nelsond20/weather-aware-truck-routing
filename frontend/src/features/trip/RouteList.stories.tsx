import type { Meta,StoryObj } from '@storybook/react-vite';
import { expect,fn,userEvent } from 'storybook/test';
import { RouteList } from './RouteList';
import { sampleTrip } from '../../test/fixtures';
const blocked=structuredClone(sampleTrip);const first=blocked.routes[0];if(!first)throw Error('Missing route');first.blocked=true;blocked.recommendation.route_id=blocked.routes[1]?.route_id??null;
const allBlocked=structuredClone(blocked);allBlocked.routes.forEach(r=>{r.blocked=true;});allBlocked.recommendation={...allBlocked.recommendation,status:'all_blocked',route_id:null};
const meta={component:RouteList,args:{trip:sampleTrip,selectedRouteId:null,onSelectRoute:fn()}} satisfies Meta<typeof RouteList>;
export default meta;type Story=StoryObj<typeof meta>;
export const Recommended:Story={};
export const AllBlocked:Story={args:{trip:allBlocked}};
export const Incomplete:Story={args:{trip:{...sampleTrip,recommendation:{...sampleTrip.recommendation,status:'insufficient_data',route_id:null}}}};
export const OneAlternative:Story={args:{trip:{...sampleTrip,routes:sampleTrip.routes.slice(0,1)}}};
export const SelectBlocked:Story={args:{trip:blocked},play:async({canvas,args})=>{
  const button=canvas.getByRole('button',{name:/Inspect route 1/});
  await userEvent.tab();await expect(button).toHaveFocus();await userEvent.keyboard('{Enter}');
  await expect(args.onSelectRoute).toHaveBeenCalledWith(first.route_id);
  await expect(canvas.getByRole('article',{name:'Route 1'})).not.toHaveTextContent('Recommended');
}};

import type { Meta,StoryObj } from '@storybook/react-vite';
import { expect,fn,userEvent } from 'storybook/test';
import { TripForm } from './TripForm';
const places=[{candidate_id:'west',label:'West Depot · Synthetic origin',coordinate:[-100,40] as [number,number]},{candidate_id:'east',label:'East Depot · Synthetic destination',coordinate:[-98,40] as [number,number]}];
const meta={component:TripForm,args:{onSubmit:fn(),searchPlaces:fn(async(query:string)=>places.filter(p=>p.label.toLowerCase().includes(query.toLowerCase()))),pending:false}} satisfies Meta<typeof TripForm>;
export default meta;type Story=StoryObj<typeof meta>;
export const Initial:Story={};
export const Submitting:Story={args:{pending:true}};
export const InvalidDeparture:Story={play:async({canvas,args})=>{
  const departure=canvas.getByRole('textbox',{name:'Departure time (include UTC offset)'});
  await userEvent.clear(departure);await userEvent.type(departure,'2026-11-01T01:30:00');
  await userEvent.click(canvas.getByRole('button',{name:'Evaluate routes'}));
  await expect(canvas.getByRole('alert')).toHaveTextContent(/offset/i);await expect(args.onSubmit).not.toHaveBeenCalled();
}};
export const AmbiguousLocation:Story={play:async({canvas,args})=>{
  await userEvent.type(canvas.getByRole('textbox',{name:'Origin'}),'West');
  await userEvent.click(canvas.getByRole('button',{name:'Evaluate routes'}));
  await expect(canvas.getByRole('alert')).toHaveTextContent(/choose/i);await expect(args.onSubmit).not.toHaveBeenCalled();
}};
export const SelectAndSubmit:Story={play:async({canvas,args})=>{
  await userEvent.type(canvas.getByRole('textbox',{name:'Origin'}),'West');
  const west=await canvas.findByRole('button',{name:'West Depot · Synthetic origin'});
  await userEvent.tab();await userEvent.keyboard('{Enter}');await expect(west).not.toBeInTheDocument();
  await userEvent.type(canvas.getByRole('textbox',{name:'Destination'}),'East');
  await userEvent.click(await canvas.findByRole('button',{name:'East Depot · Synthetic destination'}));
  await userEvent.click(canvas.getByRole('button',{name:'Evaluate routes'}));
  await expect(args.onSubmit).toHaveBeenCalledWith(expect.objectContaining({load_lb:30000,origin:{longitude:-100,latitude:40}}));
}};

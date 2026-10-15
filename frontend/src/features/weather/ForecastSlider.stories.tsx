import type { Meta,StoryObj } from '@storybook/react-vite';
import { expect,fn,userEvent } from 'storybook/test';
import { ForecastSlider } from './ForecastSlider';
import { sampleCorridor } from '../../test/fixtures';
const meta={component:ForecastSlider,args:{frames:sampleCorridor.frames,selectedFrame:0,onSelectFrame:fn(),coverage:{known_samples:2,total_samples:2},baseTime:sampleCorridor.base_time}} satisfies Meta<typeof ForecastSlider>;
export default meta;type Story=StoryObj<typeof meta>;
export const Default:Story={};
export const LastHour:Story={args:{selectedFrame:48}};
export const Unknown:Story={args:{coverage:{known_samples:0,total_samples:2}}};
export const LoadAdjustedBlocked:Story={args:{frames:sampleCorridor.frames.map(f=>({...f,levels:['no_travel','no_travel']}))}};
export const LastFrame:Story={play:async({canvas,args})=>{
  await userEvent.tab();await expect(canvas.getByRole('slider',{name:'Forecast hour'})).toHaveFocus();await expect(args.onSelectFrame).not.toHaveBeenCalled(); // Native End is verified with Playwright: Storybook user-event cannot synthesize range defaults.
}};

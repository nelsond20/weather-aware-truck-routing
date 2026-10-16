import { test,expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';
import { fillTrip } from './helpers';
test('has no serious or critical accessibility violations before and after evaluation',async({page})=>{
  await page.goto('/');let audit=await new AxeBuilder({page}).analyze();expect(audit.violations.filter(v=>v.impact==='serious'||v.impact==='critical')).toEqual([]);
  await fillTrip(page);await page.getByRole('button',{name:'Evaluate routes'}).click();await expect(page.getByRole('slider',{name:'Forecast hour'})).toBeVisible();
  audit=await new AxeBuilder({page}).analyze();expect(audit.violations.filter(v=>v.impact==='serious'||v.impact==='critical')).toEqual([]);
});

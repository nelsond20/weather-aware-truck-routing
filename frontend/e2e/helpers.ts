import type { Page } from '@playwright/test';
export async function fillTrip(page:Page,load=30001){
  await page.getByRole('textbox',{name:'Origin'}).fill('West');
  await page.getByRole('button',{name:'West Depot · Synthetic origin'}).click();
  await page.getByRole('textbox',{name:'Destination'}).fill('East');
  await page.getByRole('button',{name:'East Depot · Synthetic destination'}).click();
  await page.getByRole('spinbutton',{name:'Truck load (lb)'}).fill(String(load));
}

import { defineConfig,devices } from '@playwright/test';
export default defineConfig({testDir:'./e2e',fullyParallel:false,workers:1,forbidOnly:!!process.env.CI,retries:0,use:{baseURL:'http://127.0.0.1:5173',trace:'retain-on-failure',launchOptions:{args:['--no-sandbox']}},projects:[{name:'desktop',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:900}}},{name:'mobile',use:{...devices['Desktop Chrome'],viewport:{width:390,height:844},isMobile:true,hasTouch:true}}],webServer:[
  {command:'../backend/.venv/bin/python ../backend/manage.py runserver 127.0.0.1:8000 --noreload',url:'http://127.0.0.1:8000/api/health/',reuseExistingServer:false,env:{DJANGO_SECRET_KEY:'local-browser-tests-only-not-a-real-secret',DJANGO_DEBUG:'1',PROVIDER_MODE:'demo'}},
  {command:'npm run dev',url:'http://127.0.0.1:5173',reuseExistingServer:false},
]});

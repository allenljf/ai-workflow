import {defineConfig} from '@playwright/test';
const base=process.env.SITE_BASE || '/';
export default defineConfig({testDir:'./tests',use:{baseURL:'http://127.0.0.1:4322'+base},webServer:{command:'npm run preview -- --port 4322 --ignore-lock',url:'http://127.0.0.1:4322'+base,reuseExistingServer:false},reporter:'list'});

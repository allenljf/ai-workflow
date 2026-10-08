import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
export default defineConfig({site:process.env.SITE_URL || 'http://localhost:4321',base:process.env.SITE_BASE || '/', integrations:[starlight({title:'AI 開發知識雷達',customCss:['./src/styles/custom.css'],defaultLocale:'root',locales:{root:{label:'繁體中文',lang:'zh-TW'}}})]});

import {test,expect} from '@playwright/test';
test('radar navigation and update states',async({page})=>{
 await page.goto('./');
 await expect(page.getByRole('heading',{name:/知識有更新，\s*工作流有證據。/})).toBeVisible();
 await expect(page.getByText('AI 整理尚未啟用',{exact:true})).toBeVisible();
 await expect(page.getByText('人類驗證另行記錄',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'來源狀態',exact:true}).first().click();
 await expect(page.getByRole('heading',{name:'來源狀態',exact:true})).toBeVisible();
});
test('public guide and candidate workflow downloads',async({page})=>{
 await page.goto('guides/');
 await expect(page.getByRole('heading',{name:'AI 開發知識雷達',exact:true})).toBeVisible();
 await page.goto('workflows/');
 await expect(page.getByRole('heading',{name:'superpowers-android-adapter · 0.2.0',exact:true})).toBeVisible();
 await expect(page.getByText('候選 / 尚無 Android 實測',{exact:true})).toHaveCount(2);
 const androidCard=page.locator('.workflow-card').filter({has:page.getByRole('heading',{name:'superpowers-android-adapter · 0.2.0',exact:true})});
 const download=androidCard.getByRole('link',{name:'下載原始 ZIP 0.2.0 ↓',exact:true});
 const response=await page.request.get((await download.getAttribute('href'))!);
 expect(response.ok()).toBe(true);
 expect((await response.body()).subarray(0,2).toString()).toBe('PK');
 await page.getByRole('link',{name:'閱讀安裝指南',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Android 工作流開始使用',exact:true})).toBeVisible();
});
test('mobile layout has no horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('./');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.goto('workflows/');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
test('untrusted titles, stale sources, and topic filter',async({page})=>{
 await page.goto('./');
 await expect(page.getByRole('link',{name:'<script>alert(1)</script>',exact:true})).toBeVisible();
 expect(await page.locator('.event-card script').count()).toBe(0);
 await page.getByLabel('主題').selectOption('android');
 await expect(page.locator('.event-card:visible')).toHaveCount(1);
 await page.goto('sources/');
 await expect(page.getByText('延遲／待確認',{exact:true})).toBeVisible();
});
test('digest page awaits human approval',async({page})=>{
 await page.goto('digests/');
 await expect(page.getByRole('heading',{name:'雙週精選',exact:true})).toBeVisible();
 await expect(page.getByText('尚無人工核准的精選')).toBeVisible();
});
test('FDE roadmap and verified downloads',async({page})=>{
 await page.goto('fde/');
 await expect(page.getByRole('heading',{name:'AI 應用工程師的交付路線',exact:true})).toBeVisible();
 await expect(page.locator('.fde-skill')).toHaveCount(12);
 await expect(page.getByText('前置：模型、工具與 context',{exact:true}).first()).toBeVisible();
 await expect(page.getByText('已停用 / 請用修正版 0.3.0',{exact:true})).toBeVisible();
 const corrected=page.getByRole('link',{name:'查看套件內容 fde-solution-adapter 0.3.0 ↗',exact:true});
 await corrected.click();
 await expect(page.getByRole('heading',{name:/fde-solution-adapter · 0\.3\.0 套件內容/})).toBeVisible();
 await expect(page.getByRole('link',{name:'下載原始 ZIP'})).toBeVisible();
 const pythonFile=page.getByRole('main').getByRole('link',{name:'bundles/fde/labs-0.3/fde_lab/__init__.py',exact:true});
 await expect(pythonFile).toBeVisible();
 await pythonFile.click();
 await expect(page).toHaveURL(/files\/bundles\/fde\/labs-03\/fde_lab\/__init__\/?$/);
 await expect(page.getByRole('main').getByRole('heading',{name:'bundles/fde/labs-0.3/fde_lab/__init__.py',exact:true})).toBeVisible();
 await page.goto('fde/');
 const md=page.getByRole('link',{name:'閱讀學習路線 MD ↗',exact:true});
 expect((await page.request.get((await md.getAttribute('href'))!)).ok()).toBe(true);
 await page.goto('fde/');
 const zip=page.getByRole('link',{name:'下載原始 ZIP 0.1.0 ↓',exact:true});
 const response=await page.request.get((await zip.getAttribute('href'))!);
 expect(response.ok()).toBe(true);expect((await response.body()).subarray(0,2).toString()).toBe('PK');
 await page.getByRole('link',{name:'閱讀 RAG 指南',exact:true}).click();
 await expect(page.getByRole('heading',{name:'現代 RAG 與長 context',exact:true})).toBeVisible();
});
test('FDE mobile and update evidence states',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 for(const route of ['fde/','fde/updates/','workflows/']){
  await page.goto(route);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 }
 await page.goto('fde/updates/');
 await expect(page.getByText('尚無人工核准的 FDE 精選',{exact:true})).toBeVisible();
 await expect(page.getByText(/AI 設定：停用/)).toBeVisible();
 await expect(page.getByText(/next_due：未公開/)).toBeVisible();
 await page.goto('guides/fde/setup');
 await expect(page.getByRole('heading',{name:'FDE 本機與選配帳號設定',exact:true})).toBeVisible();
 const md=await page.request.get('downloads/fde/setup.md');expect(md.ok()).toBe(true);
 await page.goto('fde/updates/');
 await expect(page.getByRole('link',{name:'<script>alert(1)</script>',exact:true})).toBeVisible();
 expect(await page.locator('.event-card script').count()).toBe(0);
});
test('knowledge landscape and downloadable research index',async({page})=>{
 await page.goto('knowledge/');
 await expect(page.getByRole('heading',{name:'工作流知識總覽',exact:true})).toBeVisible();
 await page.getByRole('link',{name:'閱讀 Markdown ↗',exact:true}).click();
 await expect(page.getByRole('heading',{name:/AI 軟體開發工作流知識總覽/}).first()).toBeVisible();
 const download=page.getByRole('link',{name:'下載本文 Markdown',exact:true});
 const md=await page.request.get((await download.getAttribute('href'))!);
 expect(md.ok()).toBe(true);expect(await md.text()).toContain('Task graph');
 await page.goto('knowledge/');
 await page.getByRole('link',{name:'閱讀目前知識總覽',exact:true}).click();
 await expect(page.getByRole('heading',{name:/AI 軟體開發工作流知識總覽/}).first()).toBeVisible();
 const index=await page.request.get('downloads/knowledge/index.md');expect(index.ok()).toBe(true);
 await page.setViewportSize({width:390,height:844});await page.goto('knowledge/');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
test('operations guide and latest list pagination',async({page})=>{
 await page.goto('./');
 await expect(page.getByText('01 / 每週蒐集',{exact:true})).toBeVisible();
 await page.evaluate(()=>{
  const list=document.querySelector('.event-list')!;
  const card=list.querySelector('.event-card')!;
  for(let i=0;i<28;i++)list.appendChild(card.cloneNode(true));
 });
 await page.getByLabel('主題').selectOption('all');
 await expect(page.locator('.event-list .event-card:visible')).toHaveCount(24);
 await page.getByRole('button',{name:'下一頁',exact:true}).click();
 await expect(page.locator('.event-list .event-card:visible')).toHaveCount(6);
 await page.getByRole('link',{name:'網站排程與更新說明 ↗',exact:true}).click();
 await expect(page.getByRole('heading',{name:'網站自動排程、頁面用途與更新時機',exact:true})).toBeVisible();
 await expect(page.getByText('每週一 09:17：collect.yml',{exact:true})).toBeVisible();
});
test('downloaded Markdown and skill bundles have standalone site readers',async({page})=>{
 await page.goto('workflows/');
 const guide=page.getByRole('link',{name:'閱讀安裝指南',exact:true});
 await expect(guide).toHaveAttribute('href',/guides\/android\/getting-started/);
 await guide.click();
 await expect(page.getByRole('heading',{name:'Android 工作流開始使用',exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'下載本文 Markdown',exact:true})).toBeVisible();
 await page.goto('workflows/');
 await page.getByRole('link',{name:'查看套件內容 superpowers-android-adapter 0.2.0 ↗',exact:true}).click();
 await expect(page).toHaveURL(/guides\/bundles\/superpowers-android-adapter-020/);
 await expect(page.getByRole('heading',{name:/superpowers-android-adapter · 0\.2\.0 套件內容/})).toBeVisible();
 await expect(page.getByRole('main').getByRole('link',{name:'bundles/android-task/README-0.2.md',exact:true})).toBeVisible();
 await expect(page.getByRole('main').getByRole('link',{name:'skills/android-task/SKILL.md',exact:true})).toBeVisible();
 await expect(page.getByRole('main').getByRole('link',{name:'下載原始 ZIP',exact:true})).toBeVisible();
 await page.getByRole('main').getByRole('link',{name:'bundles/android-task/README-0.2.md',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Android task adapter bundle',exact:true})).toBeVisible();
});

import {test,expect} from '@playwright/test';
test('radar navigation and update states',async({page})=>{
 await page.goto('./');
 await expect(page.getByRole('heading',{name:/知識有更新，\s*工作流有證據。/})).toBeVisible();
 await expect(page.getByText('AI 整理尚未啟用',{exact:true})).toBeVisible();
 await expect(page.getByText('人類驗證另行記錄',{exact:true})).toBeVisible();
 await page.getByRole('link',{name:'來源狀態',exact:true}).first().click();
 await expect(page.getByRole('heading',{name:'來源狀態',exact:true})).toBeVisible();
});
test('public guide and empty workflow state',async({page})=>{
 await page.goto('guides/');
 await expect(page.getByRole('heading',{name:'AI 開發知識雷達',exact:true})).toBeVisible();
 await page.goto('workflows/');
 await expect(page.getByText('技能包尚未發布')).toBeVisible();
});
test('mobile layout has no horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('./');
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

import {test,expect} from '@playwright/test';

test('gallery, progressive cloud, floating pipeline and mesh replay',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.locator('#splash')).toBeHidden({timeout:10000});
 await expect(page.locator('.example-card')).toHaveCount(6);
 await page.screenshot({path:'test-results/gallery.png'});
 await page.locator('[data-example="bunny"]').click();
 await expect(page.locator('#loading')).toBeHidden({timeout:30000});
 await expect(page.locator('#point-count')).not.toHaveText('—');
 await expect(page.locator('#project-name')).toHaveText('Stanford Bunny');
 await page.screenshot({path:'test-results/bunny-points.png'});
 await page.locator('[data-step="4"]').click();
 await page.locator('#replay').click();
 await expect(page.locator('#replaybar')).toBeVisible();
 await page.waitForTimeout(2500);
 await page.screenshot({path:'test-results/bunny-replay.png'});
 await page.locator('#collapse').click();await expect(page.locator('#expand')).toBeVisible();
 await page.locator('#expand').click();
 await page.locator('[data-step="1"]').click();await page.locator('#execute').click();
 await expect(page.locator('#loading')).toBeHidden({timeout:30000});
 await page.locator('[data-step="2"]').click();await page.locator('#execute').click();
 await expect(page.locator('#loading')).toBeHidden({timeout:30000});
 expect(errors).toEqual([]);
});

test('mobile gallery fits screen',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await expect(page.locator('#splash')).toBeHidden({timeout:10000});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.screenshot({path:'test-results/mobile.png'});
});

test('API rejects unsafe budgets and cross-origin writes',async({request})=>{
 const bad=await request.post('/api/jobs',{data:{operation:'open',example:'bunny',params:{budget:5000000}}});
 expect(bad.status()).toBe(400);
 const cross=await request.post('/api/jobs',{headers:{Origin:'https://untrusted.example'},data:{operation:'open',example:'bunny'}});
 expect(cross.status()).toBe(403);
});

test('custom BPA settings, boundary overlay and inverted cuadra presentation',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await expect(page.locator('#splash')).toBeHidden({timeout:10000});
 await page.locator('[data-example="bunny"]').click();
 await expect(page.locator('#loading')).toBeHidden({timeout:30000});
 await page.locator('[data-step="4"]').click();
 await page.locator('#custom-radii').fill('3, 5, 8');
 await expect(page.locator('#effective-radii')).toContainText('Radios efectivos');
 await page.locator('#execute').click();
 await expect(page.locator('#loading')).toBeHidden({timeout:30000});
 await expect(page.locator('#custom-radii')).toHaveValue('3, 5, 8');
 await page.locator('#full-mesh').click();await page.locator('#show-boundaries').check();
 await page.screenshot({path:'test-results/bpa-advanced.png'});
 await page.locator('#gallery-button').click();await page.locator('[data-example="cuadra_sparse"]').click();
 await expect(page.locator('#loading')).toBeHidden({timeout:30000});
 await page.locator('[data-step="0"]').click();
 await expect(page.locator('#view-up')).toHaveValue('y-');
 await page.screenshot({path:'test-results/cuadra-upright.png'});
 await page.locator('#view-up').selectOption('z+');
 expect(errors).toEqual([]);
});

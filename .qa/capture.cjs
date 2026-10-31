const {chromium}=require('./node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const out=path.resolve(__dirname,'../docs/preview');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1080}});
 const token=fs.readFileSync(path.join(__dirname,'preview-data/dashboard-token.txt'),'utf8').trim();
 await page.addInitScript(key=>sessionStorage.setItem('desk-key',key),token);
 await page.goto('http://127.0.0.1:8901');await page.waitForFunction(()=>document.getElementById('balance').textContent!=='—');await page.evaluate(()=>document.fonts.ready);
 await page.screenshot({path:path.join(out,'dashboard-light.png'),fullPage:true,animations:'disabled'});
 await page.locator('#theme-toggle').click();await page.screenshot({path:path.join(out,'dashboard-dark.png'),fullPage:true,animations:'disabled'});await page.locator('#theme-toggle').click();
 await page.evaluate(()=>location.hash='settings');await page.waitForFunction(()=>!document.getElementById('settings').hidden);await page.screenshot({path:path.join(out,'settings.png'),fullPage:true,animations:'disabled'});
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>location.hash='overview');await page.waitForFunction(()=>!document.getElementById('overview').hidden);await page.screenshot({path:path.join(out,'dashboard-mobile.png'),fullPage:true,animations:'disabled'});
 await page.setViewportSize({width:1440,height:1080});await page.locator('#logout').click();await page.screenshot({path:path.join(out,'login.png'),animations:'disabled'});
 await browser.close();console.log('Saved five screenshots of actual paused paper preview to docs/preview');
})().catch(e=>{console.error(e);process.exitCode=1;});

// UI-only smoke test. All mutations below are intercepted and never reach a trading engine.
const {chromium}=require('./node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const base='http://127.0.0.1:8901';
const token=fs.readFileSync(path.join(__dirname,'preview-data/dashboard-token.txt'),'utf8').trim();
const artifacts=path.join(__dirname,'artifacts');fs.mkdirSync(artifacts,{recursive:true});
let checks=0;
function check(value,message){assert.ok(value,message);checks++;console.log('PASS '+message);}
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1080},deviceScaleFactor:1});
 const page=await context.newPage();const errors=[],csp=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')csp.push(m.text());});
 try{
  await page.goto(base);await page.evaluate(()=>document.fonts.ready);
  check(await page.locator('#login').isVisible(),'login screen visible');
  await page.screenshot({path:path.join(artifacts,'login-desktop.png')});
  await page.locator('#token').fill(token);await page.locator('#login-form button').click();await page.waitForFunction(()=>!document.getElementById('login').open);
  await page.waitForFunction(()=>document.getElementById('balance').textContent!=='—');
  check(await page.locator('#balance').textContent()==='1,000.00','real preview account balance loaded');
  check(await page.evaluate(()=>document.fonts.check('12px "DM Sans"')&&document.fonts.check('12px "Noto Sans Thai"')),'self-hosted fonts loaded');
  check(await page.locator('.view:visible').count()===1,'one route visible');
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'desktop has no horizontal overflow');
  await page.screenshot({path:path.join(artifacts,'overview-desktop.png'),fullPage:true});
  const original=await(await fetch(base+'/api/state',{headers:{Authorization:'Bearer '+token}})).json();
  let fixture=structuredClone(original);const now=Date.now()/1000;
  fixture.trades=Array.from({length:8},(_,i)=>({id:'qa-'+i,mode:'paper',symbol:i%2?'XAUUSD':'EURUSD',side:i%3?'buy':'sell',volume:.01,pnl_thb:i%3?10.5:-10.4,reason:i%3?'take_profit':'stop_loss',closed_at:now-i*130,opened_at:now-i*130-60,entry:100,exit:101}));
  let saved=null,rejectSave=false;const calls=[];
  await page.route('**/api/**',async route=>{const req=route.request(),endpoint=new URL(req.url()).pathname.split('/').at(-1);if(req.method()==='POST'){calls.push(endpoint);if(endpoint==='settings'){saved=req.postDataJSON();if(rejectSave)return route.fulfill({status:400,contentType:'application/json',body:JSON.stringify({error:'QA: settings rejected'})});fixture.config={...fixture.config,...saved};fixture.targets=fixture.config.target_mode==='percent'?[fixture.config.capital_thb*fixture.config.take_profit_pct/100,fixture.config.capital_thb*fixture.config.stop_loss_pct/100]:[fixture.config.take_profit_thb,fixture.config.stop_loss_thb];}if(endpoint==='start'){fixture.running=true;fixture.position={id:'qa-position',symbol:'EURUSD',side:'buy',entry:100,volume:.01,pnl_thb:3.2,opened_at:now};}if(endpoint==='pause')fixture.running=false;if(endpoint==='flatten'){fixture.running=false;fixture.position=null;}}
   if(endpoint==='symbols')return route.fulfill({contentType:'application/json',body:JSON.stringify([{name:'EURUSD',description:'QA symbol',path:'Forex'}])});
   return route.fulfill({contentType:'application/json',body:JSON.stringify(fixture)});
  });
  await page.waitForFunction(()=>document.getElementById('recent-trades').rows.length===5);
  check(await page.locator('#recent-trades tr').count()===5,'recent list capped at five');
  await page.locator('[data-route="history"]').click();await page.waitForFunction(()=>!document.getElementById('history').hidden);
  check(await page.locator('#trades tr').count()===8,'history shows actual fixture trades');
  await page.locator('#history-search').fill('xau');check(await page.locator('#trades tr').count()===4,'history filter matches symbol');
  await page.locator('#history-search').fill('no-such-symbol');check(await page.locator('#trades .table-empty').isVisible(),'filtered empty state');await page.locator('#history-search').fill('');
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#export').click()]);check(download.suggestedFilename()==='trading-history.csv','CSV export works');
  await page.locator('[data-route="settings"]').click();check(await page.locator('#settings').isVisible(),'settings route opens');
  await page.locator('select[name="target_mode"]').selectOption('percent');check(await page.locator('[data-target="percent"]').first().isVisible(),'percent fields appear');check(!await page.locator('[data-target="fixed"]').first().isVisible(),'fixed fields hidden in percent mode');
  await page.locator('input[name="take_profit_pct"]').fill('1.5');await page.locator('#save').click();await page.waitForFunction(()=>document.getElementById('toast').textContent==='บันทึกการตั้งค่าแล้ว');check(saved.target_mode==='percent'&&saved.take_profit_pct===1.5,'settings save retains API contract');
  await page.screenshot({path:path.join(artifacts,'settings-desktop.png'),fullPage:true});
  rejectSave=true;await page.locator('input[name="capital_thb"]').fill('1234');await page.locator('#save').click();await page.waitForFunction(()=>document.getElementById('toast').textContent==='QA: settings rejected');check(await page.locator('input[name="capital_thb"]').inputValue()==='1234','failed save preserves edits');rejectSave=false;
  await page.locator('[data-route="overview"]').click();await page.locator('#start').click();await page.waitForFunction(()=>document.getElementById('status').textContent==='กำลังทำงาน');check(await page.locator('#position-details').isVisible(),'position renders after start');check(await page.locator('#start').isDisabled(),'start disabled while running');
  await page.locator('[data-route="settings"]').click();check(await page.locator('input[name="symbol"]').isDisabled(),'settings locked with active trade');
  await page.locator('[data-route="overview"]').click();await page.locator('#pause').click();await page.waitForFunction(()=>document.getElementById('status').textContent==='พักอยู่');check(await page.locator('#position-details').isVisible(),'pause keeps open position visible');
  await page.locator('#flatten').click();check(await page.locator('#confirm-close').isVisible(),'flatten confirmation visible');await page.locator('#cancel-close').click();check(!calls.includes('flatten'),'cancel does not send flatten');
  await page.locator('#flatten').click();await page.locator('#confirm-flatten').click();await page.waitForFunction(()=>!document.getElementById('position-empty').hidden);check(calls.includes('flatten'),'confirm sends existing flatten endpoint');
  await page.locator('#theme-toggle').click();check(await page.locator('html').getAttribute('data-theme')==='dark','dark mode works');await page.screenshot({path:path.join(artifacts,'overview-dark.png'),fullPage:true});
  await page.reload();await page.waitForFunction(()=>document.getElementById('balance').textContent!=='—');check(await page.locator('html').getAttribute('data-theme')==='dark','theme survives reload');await page.locator('#theme-toggle').click();
  await page.locator('#page-search').fill('telegram');await page.locator('#page-search').press('Enter');await page.waitForFunction(()=>!document.getElementById('alerts').hidden);check(await page.locator('#alerts').isVisible(),'search navigates to alerts');
  await page.locator('[data-route="setup"]').click();check(await page.locator('.setup-steps li').count()===5,'account guide route intact');
  for(const width of [320,390,768,1024,1440]){
    await page.setViewportSize({width,height:1000});
    for(const name of ['overview','settings','history','alerts','setup']){
      await page.evaluate(name=>{location.hash=name;},name);await page.waitForFunction(name=>!document.getElementById(name).hidden,name);
      const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
      check(!overflow,width+'px '+name+' no page overflow');
    }
  }
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>{location.hash='overview';});await page.waitForFunction(()=>!document.getElementById('overview').hidden);
  await page.screenshot({path:path.join(artifacts,'overview-mobile.png'),fullPage:true,animations:'disabled'});
  await page.locator('#menu-toggle').click();check(await page.locator('#sidebar').evaluate(el=>el.classList.contains('open')),'mobile drawer opens');await page.locator('[data-route="settings"]').click();check(await page.locator('#nav-backdrop').isHidden(),'mobile drawer closes on navigation');
  await page.route('**/api/state',route=>route.abort());await page.waitForFunction(()=>document.getElementById('connection-wrap').classList.contains('error'));await page.evaluate(()=>{location.hash='overview';});check(await page.locator('#start').isDisabled(),'offline disables order controls');
  await page.unroute('**/api/state');await page.waitForFunction(()=>!document.getElementById('start').disabled);check(await page.locator('#start').isEnabled(),'polling recovers after connection returns');
  await page.locator('#logout').click();check(await page.locator('#login').isVisible(),'lock returns to login');check(await page.evaluate(()=>sessionStorage.getItem('desk-key'))===null,'lock clears session key');
  await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:path.join(artifacts,'login-mobile.png'),fullPage:true});
  check(errors.length===0,'no browser JavaScript errors: '+errors.join(', '));check(!csp.some(s=>/Content Security Policy|Refused to/.test(s)),'no CSP violations');
  fs.writeFileSync(path.join(artifacts,'results.json'),JSON.stringify({checks,errors,consoleErrors:csp,mutationsIntercepted:calls},null,2));
  console.log('SUCCESS '+checks+' UI checks; order mutations intercepted, no real orders');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});

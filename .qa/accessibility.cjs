const {chromium}=require('./node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1080}});
 const token=fs.readFileSync(path.join(__dirname,'preview-data/dashboard-token.txt'),'utf8').trim();
 await page.addInitScript(key=>sessionStorage.setItem('desk-key',key),token);
 await page.goto('http://127.0.0.1:8901');await page.waitForFunction(()=>document.getElementById('balance').textContent!=='—');await page.evaluate(()=>document.fonts.ready);
 await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));
 const all=[];
 for(const theme of ['light','dark']){
  await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
  for(const route of ['overview','settings','history','alerts','setup']){
   await page.evaluate(route=>location.hash=route,route);await page.waitForFunction(route=>!document.getElementById(route).hidden,route);
   const result=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));});
   all.push({theme,route,violations:result});console.log(theme+' '+route+': '+JSON.stringify(result.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))));
  }
 }
 await page.setViewportSize({width:390,height:844});
 for(const route of ['overview','settings','history','alerts','setup']){
  await page.evaluate(route=>location.hash=route,route);await page.waitForFunction(route=>!document.getElementById(route).hidden,route);
  const result=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));});
  all.push({theme:'dark-mobile',route,violations:result});console.log('dark-mobile '+route+': '+JSON.stringify(result.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))));
 }
 await page.locator('#logout').click();await page.evaluate(()=>document.fonts.ready);
 for(const theme of ['light','dark']){
  await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
  const result=await page.evaluate(async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}));});
  all.push({theme,route:'login-mobile',violations:result});console.log(theme+' login-mobile: '+JSON.stringify(result.map(v=>({id:v.id,nodes:v.nodes.map(n=>n.target)}))));
 }
 fs.writeFileSync(path.join(__dirname,'artifacts/accessibility.json'),JSON.stringify(all,null,2));
 await browser.close();if(all.some(r=>r.violations.length))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1;});

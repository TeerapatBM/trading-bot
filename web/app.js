'use strict';
const $ = id => document.getElementById(id);
const form = $('settings-form');
const routes = {
  overview: {title:'ภาพรวมการเทรด',label:'ภาพรวม',keywords:'dashboard overview ภาพรวม กราฟ'},
  settings: {title:'ตั้งค่าบอต',label:'ตั้งค่าบอต',keywords:'settings bot ตั้งค่า เป้า lot กลยุทธ์'},
  history: {title:'ประวัติการเทรด',label:'ประวัติการเทรด',keywords:'history trades ประวัติ ออเดอร์ ผลลัพธ์ csv'},
  alerts: {title:'การแจ้งเตือน',label:'การแจ้งเตือน',keywords:'alerts telegram แจ้งเตือน กิจกรรม'},
  setup: {title:'เชื่อมต่อบัญชี',label:'เชื่อมต่อบัญชี',keywords:'setup xm mt5 บัญชี เชื่อมต่อ คู่มือ'}
};
let key = sessionStorage.getItem('desk-key') || '';
let state = null, formLoaded = false, busy = false, refreshing = false, connected = false;
let currentRoute = 'overview', mutationVersion = 0, selectedPoint = null;
const money = n => n == null ? '—' : new Intl.NumberFormat('th-TH',{minimumFractionDigits:2,maximumFractionDigits:2}).format(n);
const clock = t => new Date(t*1000).toLocaleTimeString('th-TH',{timeZone:'Asia/Bangkok',hour12:false});
const stamp = t => new Date(t*1000).toLocaleString('th-TH',{timeZone:'Asia/Bangkok',hour12:false});
const signed = n => (n>0?'+':'')+money(n);
function text(id,value){$(id).textContent=value;}
function paintNumber(id,value){text(id,money(value));$(id).classList.toggle('positive',value>0);$(id).classList.toggle('negative',value<0);}
function icon(name){const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.classList.add('icon');svg.setAttribute('aria-hidden','true');const use=document.createElementNS(svg.namespaceURI,'use');use.setAttribute('href','#i-'+name);svg.append(use);return svg;}
function toast(message,error=false){text('toast',message);$('toast').hidden=false;$('toast').setAttribute('role',error?'alert':'status');clearTimeout(toast.timer);toast.timer=setTimeout(()=>{$('toast').hidden=true;},6500);}
function setMenu(open){const sidebar=$('sidebar'),wasInside=sidebar.contains(document.activeElement);sidebar.classList.toggle('open',open);sidebar.inert=innerWidth<=800&&!open;$('nav-backdrop').hidden=!open;$('menu-toggle').setAttribute('aria-expanded',String(open));$('menu-toggle').setAttribute('aria-label',open?'ปิดเมนู':'เปิดเมนู');if(open)sidebar.querySelector('[aria-current="page"]')?.focus();else if(wasInside)$('page-title').focus({preventScroll:true});}
function navigate(){
  const hash=location.hash.slice(1),next=Object.hasOwn(routes,hash)?hash:'overview';
  if(hash==='main'){document.querySelector('h1').focus();return;}
  currentRoute=next;
  for(const name of Object.keys(routes))$(name).hidden=name!==next;
  document.querySelectorAll('[data-route]').forEach(link=>{const active=link.dataset.route===next;link.classList.toggle('active',active);if(active)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
  $('page-title').replaceChildren(document.createTextNode(routes[next].title));const dot=document.createElement('span');dot.className='title-dot';dot.textContent='.';$('page-title').append(dot);
  text('breadcrumb-title',routes[next].label);document.title='Trading Desk · '+routes[next].label;
  setMenu(false);$('search-results').hidden=true;window.scrollTo({top:0,behavior:'instant'});
  if(next==='overview'&&state)requestAnimationFrame(()=>draw(state.chart));
}
function setTheme(theme){document.documentElement.dataset.theme=theme;localStorage.setItem('desk-theme',theme);const dark=theme==='dark';$('theme-toggle').setAttribute('aria-pressed',String(dark));$('theme-toggle').setAttribute('aria-label',dark?'เปลี่ยนเป็นโหมดสว่าง':'เปลี่ยนเป็นโหมดมืด');$('theme-icon').setAttribute('href',dark?'#i-sun':'#i-moon');if(state)draw(state.chart);}
function lockScreen(){key='';connected=false;sessionStorage.removeItem('desk-key');$('login-error').textContent='';$('token').value='';if(!$('login').open)$('login').showModal();updateControls();}
async function api(path,payload){
  const res=await fetch('/api/'+path,{method:payload===undefined?'GET':'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:payload===undefined?undefined:JSON.stringify(payload),signal:AbortSignal.timeout(20000)});
  const data=await res.json();
  if(res.status===401){lockScreen();throw Error('รหัสเข้าใช้งานไม่ถูกต้อง');}
  if(!res.ok)throw Error(data.error||'คำสั่งไม่สำเร็จ');
  return data;
}
function updateControls(){
  const locked=!!state&&(state.running||!!state.position),unavailable=busy||!connected||!key;
  $('start').disabled=unavailable||!!state?.running;
  $('pause').disabled=unavailable||!state?.running;
  $('flatten').disabled=unavailable;
  $('settings-fields').disabled=locked||busy||!connected;
  $('save').disabled=locked||unavailable;
  $('load-symbols').disabled=unavailable;
  $('test-alert').disabled=unavailable;
  $('confirm-flatten').disabled=unavailable;
  text('settings-lock',locked?'พักและปิดสถานะก่อนแก้':!connected?'กำลังรอการเชื่อมต่อ':'แก้ไขได้');
  $('save').setAttribute('aria-busy',String(busy));
}
function targetFields(){const mode=form.elements.target_mode.value;document.querySelectorAll('[data-target]').forEach(label=>{label.hidden=label.dataset.target!==mode;label.querySelector('input').required=!label.hidden;});}
function fillForm(c){for(const [name,value]of Object.entries(c))if(form.elements[name])form.elements[name].value=value;formLoaded=true;targetFields();}
function draw(allPoints){
  if(currentRoute!=='overview')return;
  const points=allPoints.slice(-Number($('chart-window').value)),canvas=$('chart');
  const bounds=canvas.getBoundingClientRect(),width=bounds.width,height=bounds.height,ratio=window.devicePixelRatio||1;
  if(width<1||height<1)return;
  canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
  const ctx=canvas.getContext('2d');ctx.scale(ratio,ratio);
  const css=getComputedStyle(document.documentElement),line=css.getPropertyValue('--line').trim(),purple=css.getPropertyValue('--purple').trim(),muted=css.getPropertyValue('--soft-text').trim();
  const pad={left:8,right:61,top:20,bottom:28},w=width-pad.left-pad.right,h=height-pad.top-pad.bottom;
  if(points.length<2){ctx.fillStyle=muted;ctx.font='11px "Noto Sans Thai"';ctx.textAlign='center';ctx.fillText('รอข้อมูลราคา…',width/2,height/2);text('range','—');return;}
  let lo=Math.min(...points.map(p=>p.price)),hi=Math.max(...points.map(p=>p.price));
  const margin=Math.max((hi-lo)*.2,Math.abs(hi)*.00001);lo-=margin;hi+=margin;
  const digits=Math.abs(hi)<10?5:3;
  ctx.font='9px "DM Sans"';ctx.lineWidth=1;ctx.strokeStyle=line;ctx.fillStyle=muted;
  for(let i=0;i<5;i++){const y=pad.top+i*h/4;ctx.setLineDash([3,5]);ctx.beginPath();ctx.moveTo(pad.left,y);ctx.lineTo(pad.left+w,y);ctx.stroke();ctx.setLineDash([]);ctx.fillText((hi-(hi-lo)*i/4).toFixed(digits),pad.left+w+9,y+3);}
  const x=i=>pad.left+i*w/(points.length-1),y=p=>pad.top+(hi-p)/(hi-lo)*h;
  ctx.beginPath();points.forEach((p,i)=>i?ctx.lineTo(x(i),y(p.price)):ctx.moveTo(x(i),y(p.price)));
  ctx.lineWidth=2.8;ctx.strokeStyle=purple;ctx.lineJoin='round';ctx.lineCap='round';ctx.stroke();
  ctx.lineTo(x(points.length-1),pad.top+h);ctx.lineTo(pad.left,pad.top+h);ctx.closePath();
  const gradient=ctx.createLinearGradient(0,pad.top,0,pad.top+h);gradient.addColorStop(0,purple+'20');gradient.addColorStop(1,purple+'00');ctx.fillStyle=gradient;ctx.fill();
  const last=points.at(-1);ctx.beginPath();ctx.arc(x(points.length-1),y(last.price),3.5,0,Math.PI*2);ctx.fillStyle=purple;ctx.fill();
  ctx.fillStyle=muted;ctx.font='9px "DM Sans"';ctx.textAlign='left';ctx.fillText(clock(points[0].time),pad.left,height-6);ctx.textAlign='right';ctx.fillText(clock(last.time),pad.left+w,height-6);
  if(selectedPoint!==null){const i=Math.max(0,Math.min(points.length-1,Math.round(selectedPoint*(points.length-1))));const p=points[i];ctx.beginPath();ctx.setLineDash([3,4]);ctx.strokeStyle=muted;ctx.lineWidth=1;ctx.moveTo(x(i),pad.top);ctx.lineTo(x(i),pad.top+h);ctx.stroke();ctx.setLineDash([]);ctx.beginPath();ctx.arc(x(i),y(p.price),4,0,Math.PI*2);ctx.fillStyle=purple;ctx.fill();ctx.textAlign='left';ctx.fillStyle=css.getPropertyValue('--ink').trim();ctx.font='10px "DM Sans"';ctx.fillText(clock(p.time)+' · '+p.price.toFixed(5),pad.left+3,11);}
  text('range',lo.toFixed(digits)+' – '+hi.toFixed(digits));
  const change=(last.price-points[0].price)/points[0].price*100;text('price-change',(change>=0?'+':'')+change.toFixed(3)+'% ในช่วงที่แสดง');$('price-change').classList.toggle('positive',change>=0);$('price-change').classList.toggle('negative',change<0);
}
function emptyTable(body,colspan,filtered=false){const row=body.insertRow(),cell=row.insertCell();cell.colSpan=colspan;cell.className='table-empty';const strong=document.createElement('strong'),p=document.createElement('p');strong.textContent=filtered?'ไม่พบรายการที่ค้นหา':'ยังไม่มีรอบที่ปิดแล้ว';p.textContent=filtered?'ลองค้นหาด้วยชื่อสินทรัพย์หรือ Buy / Sell':'เมื่อบอตปิดออเดอร์ ผลลัพธ์จะแสดงที่นี่';cell.append(icon('history'),strong,p);}
function assetCell(row,trade){const cell=row.insertCell(),wrap=document.createElement('div');wrap.className='asset-cell';const badge=document.createElement('span');badge.className='asset-icon';badge.textContent=trade.symbol.slice(0,2);const name=document.createElement('span');name.className='asset-name';name.textContent=trade.symbol;wrap.append(badge,name);cell.append(wrap);}
function sideCell(row,side){const badge=document.createElement('span');badge.className='side-badge '+side;badge.textContent=side.toUpperCase();row.insertCell().append(badge);}
function resultCell(row,pnl){const cell=row.insertCell();cell.textContent=signed(pnl);cell.className=pnl>=0?'positive':'negative';}
function renderTrades(trades){
  const recent=$('recent-trades');recent.replaceChildren();
  if(!trades.length)emptyTable(recent,4);
  for(const t of trades.slice(0,5)){const row=recent.insertRow();assetCell(row,t);row.insertCell().textContent=clock(t.closed_at);sideCell(row,t.side);resultCell(row,t.pnl_thb);}
  const total=trades.reduce((sum,t)=>sum+t.pnl_thb,0),wins=trades.filter(t=>t.pnl_thb>0).length;
  text('trade-summary',trades.length?trades.length+' รอบที่แสดง · รวม '+signed(total)+' THB':'ผลจะแสดงหลังปิดออเดอร์แรก');
  text('history-count',trades.length);paintNumber('history-total',trades.length?total:null);text('history-winrate',trades.length?(wins/trades.length*100).toFixed(1)+'%':'—');
  const query=$('history-search').value.trim().toLowerCase(),filtered=trades.filter(t=>(t.symbol+' '+t.side).toLowerCase().includes(query));
  const body=$('trades');body.replaceChildren();if(!filtered.length)emptyTable(body,6,!!query);
  const reasons={take_profit:'ปิดกำไร',stop_loss:'ปิดขาดทุน',manual:'ปิดด้วยตนเอง',broker:'ปิดจากโบรกเกอร์'};
  for(const t of filtered){const row=body.insertRow();assetCell(row,t);row.insertCell().textContent=stamp(t.closed_at);sideCell(row,t.side);row.insertCell().textContent=t.volume;resultCell(row,t.pnl_thb);row.insertCell().textContent=reasons[t.reason]||t.reason;}
  const cumulative=[0];for(const t of trades.slice(0,12).reverse())cumulative.push(cumulative.at(-1)+t.pnl_thb);
  const low=Math.min(...cumulative),high=Math.max(...cumulative),range=high-low||1;
  $('daily-spark-path').setAttribute('d',cumulative.map((v,i)=>(i?'L':'M')+(2+i*68/Math.max(1,cumulative.length-1)).toFixed(1)+' '+(28-(v-low)/range*24).toFixed(1)).join(' '));
  if(!trades.length)$('daily-spark-path').setAttribute('d','M2 16H70');
  $('daily-spark').setAttribute('aria-label',trades.length?'ผลสะสมของ '+Math.min(trades.length,12)+' รอบล่าสุด':'ยังไม่มีผลรอบที่ปิด');
}
function renderEvents(events){
  const names={start:'เริ่มทำงาน',pause:'พักบอต',flatten:'ปิดสถานะ',order:'เปิดออเดอร์',trade:'ปิดรอบ',error:'ข้อผิดพลาด',settings:'ตั้งค่า',limit:'ขีดจำกัด',report:'สรุปผล',test:'ทดสอบแจ้งเตือน'};
  const icons={start:'play',pause:'pause',flatten:'stop',order:'trend',trade:'check',error:'info',settings:'settings',limit:'shield',report:'chart',test:'send'};
  const body=$('events');body.replaceChildren();
  if(!events.length){const empty=document.createElement('p');empty.className='empty-events';empty.textContent='ยังไม่มีกิจกรรม · เหตุการณ์ของบอตจะแสดงที่นี่';body.append(empty);}
  for(const e of events){const row=document.createElement('div');row.className='event';const mark=document.createElement('span');mark.className='event-icon'+(e.kind==='error'?' error':'');mark.append(icon(icons[e.kind]||'info'));const content=document.createElement('div');content.className='event-body';const message=document.createElement('div');message.textContent=e.message;const kind=document.createElement('small');kind.textContent=names[e.kind]||e.kind;content.append(message,kind);const when=document.createElement('time');when.textContent=clock(e.time);when.dateTime=new Date(e.time*1000).toISOString();when.title=stamp(e.time);row.append(mark,content,when);body.append(row);}
  const errors=events.filter(e=>e.kind==='error').length;text('alert-count',errors);$('alert-count').hidden=!errors;$('notification-dot').hidden=!errors;
}
function render(s){
  state=s;connected=true;const c=s.config,mt5=c.mode==='mt5',p=s.position;
  text('mode',mt5?(s.account?.real?'MT5 · เงินจริง':s.account?'MT5 · Demo':'MT5 · รอเชื่อมต่อ'):'Paper · บัญชีจำลอง');$('mode').parentElement.classList.toggle('live',!!s.account?.real);
  text('sidebar-mode',mt5?(s.account?.real?'Live account':'MT5 account'):'Paper account');
  text('status',s.running?'กำลังทำงาน':'พักอยู่');$('status').classList.toggle('running',s.running);
  text('bot-rule',c.entry_mode==='continuous'?'หนึ่งออเดอร์ต่อครั้ง · เปิดรอบถัดไปต่อเนื่อง':'หนึ่งออเดอร์ต่อครั้ง · รอสัญญาณก่อนเปิดรอบใหม่');
  text('instrument',c.symbol);const stale=s.last_tick==null||Date.now()/1000-s.last_tick>10;
  text('freshness',s.last_tick?'อัปเดต '+clock(s.last_tick):'ยังไม่มีราคา');
  text('connection',s.error||(stale?'ขาดการอัปเดตราคา: ตรวจโปรแกรมและ MT5':mt5?'เชื่อมต่อ MT5 · เป้าบาทใช้อัตราที่ตั้งเอง · SL/TP เก็บที่โบรกเกอร์':'Paper trading · ราคาสังเคราะห์สำหรับทดลองระบบ ไม่ใช่ราคาตลาดจริง'));
  $('connection-wrap').classList.toggle('error',!!s.error||stale);
  text('balance',money(s.balance));text('equity',money(s.equity));paintNumber('daily',s.daily_pnl);text('target','+'+money(s.targets[0])+' / −'+money(s.targets[1]));
  text('chart-title',c.symbol);text('feed-label',mt5?'MT5 feed':'Paper feed');text('chart-note',mt5?'ราคากลาง Bid / Ask จาก MT5':'ราคาสังเคราะห์ ไม่ใช่ราคาของสินทรัพย์จริง');text('price',s.chart.length?s.chart.at(-1).price.toFixed(5):'—');draw(s.chart);
  text('position-side',p?p.side.toUpperCase():'ไม่มีสถานะ');$('position-side').className='pill'+(p?' '+p.side:'');$('position-empty').hidden=!!p;$('position-details').hidden=!p;
  if(p){text('pos-symbol',p.symbol);text('pos-entry',Number(p.entry).toFixed(5));text('pos-volume',p.volume);paintNumber('pos-pnl',p.pnl_thb);text('pos-time',clock(p.opened_at));}
  text('signal',({buy:'แนวโน้มขึ้น · Buy',sell:'แนวโน้มลง · Sell',wait:'รอข้อมูล / สัญญาณ'})[s.analysis.side]);text('reason',s.analysis.reason);text('signal-mode',c.entry_mode==='continuous'?'เปิดรอบต่อเนื่อง':'เปิดเมื่อมีสัญญาณ');
  text('risk-used',money(Math.max(0,-s.daily_pnl)));text('risk-limit',money(c.daily_loss_thb));$('risk-progress').value=Math.min(100,Math.max(0,-s.daily_pnl)/c.daily_loss_thb*100);
  if(!formLoaded)fillForm(c);renderTrades(s.trades);renderEvents(s.events);
  text('telegram-status',s.alerts.configured?(s.alerts.error||'เชื่อมต่อแล้ว · ส่งสำเร็จ '+s.alerts.sent+' ข้อความ'):'ยังไม่ได้เชื่อม Telegram');
  text('account-info',s.account?`บัญชี ${s.account.login} · ${s.account.server}\n${s.account.real?'เงินจริง':'Demo / บัญชีทดสอบ'} · ${s.account.currency}\n1 หน่วย = ${s.account.conversion} THB`:'ยังไม่เชื่อมบัญชี MT5');updateControls();
}
async function refresh(){if(!key||refreshing||busy)return;refreshing=true;const version=mutationVersion;try{const s=await api('state');if(version===mutationVersion&&!busy)render(s);}catch(e){if(version===mutationVersion){connected=false;text('connection',e.message+' · ตรวจว่า run.py ยังทำงานอยู่');$('connection-wrap').classList.add('error');updateControls();}}finally{refreshing=false;}}
async function action(name,payload={}){
  if(busy)return false;busy=true;mutationVersion++;updateControls();
  try{const s=await api(name,payload);if(name==='settings')fillForm(s.config);render(s);const messages={start:'เริ่มบอตแล้ว',pause:'พักเปิดออเดอร์ใหม่แล้ว',flatten:'ส่งคำสั่งปิดสถานะและพักบอตแล้ว',settings:'บันทึกการตั้งค่าแล้ว','test-alert':'เข้าคิวส่ง Telegram แล้ว ตรวจสถานะการส่งในหน้านี้'};toast(messages[name]||'ดำเนินการแล้ว');return true;}
  catch(e){toast(e.message,true);return false;}
  finally{busy=false;updateControls();refresh();}
}
$('login-form').addEventListener('submit',async e=>{e.preventDefault();const button=e.currentTarget.querySelector('button');button.disabled=true;key=$('token').value.trim();try{const s=await api('state');sessionStorage.setItem('desk-key',key);$('token').value='';$('login').close();render(s);}catch(err){text('login-error',err.message);}finally{button.disabled=false;}});
$('login').addEventListener('cancel',e=>e.preventDefault());$('logout').addEventListener('click',lockScreen);
$('start').addEventListener('click',()=>action('start'));$('pause').addEventListener('click',()=>action('pause'));$('flatten').addEventListener('click',()=>$('confirm-close').showModal());$('cancel-close').addEventListener('click',()=>$('confirm-close').close());$('confirm-flatten').addEventListener('click',()=>{$('confirm-close').close();action('flatten');});$('test-alert').addEventListener('click',()=>action('test-alert'));
form.addEventListener('submit',async e=>{e.preventDefault();const payload={};for(const [name,value]of new FormData(form)){const field=form.elements[name],hidden=field.closest('[data-target]')?.hidden;payload[name]=hidden?state.config[name]:['mode','symbol','entry_mode','target_mode'].includes(name)?value:Number(value);}await action('settings',payload);});
form.elements.target_mode.addEventListener('change',targetFields);
$('load-symbols').addEventListener('click',async()=>{const button=$('load-symbols');button.disabled=true;try{const list=await api('symbols');$('symbols').replaceChildren();for(const s of list){const option=document.createElement('option');option.value=s.name;option.label=s.description+' · '+s.path;$('symbols').append(option);}toast('โหลด '+list.length+' สินทรัพย์แล้ว พิมพ์ชื่อในช่องสินทรัพย์');form.elements.symbol.focus();}catch(e){toast(e.message,true);}finally{updateControls();}});
$('history-search').addEventListener('input',()=>{if(state)renderTrades(state.trades);});
$('export').addEventListener('click',()=>{if(!state)return;const rows=[['closed_at_bangkok','symbol','side','volume','pnl_thb','reason'],...state.trades.map(t=>[stamp(t.closed_at),t.symbol,t.side,t.volume,t.pnl_thb,t.reason])];const quote=v=>'"'+String(v).replace(/^[=+@\-]/,"'").replaceAll('"','""')+'"';const csv='\ufeff'+rows.map(r=>r.map(quote).join(',')).join('\r\n');const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='trading-history.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('chart-window').addEventListener('change',()=>{selectedPoint=null;if(state)draw(state.chart);});$('chart').addEventListener('pointermove',e=>{const rect=e.currentTarget.getBoundingClientRect();selectedPoint=Math.max(0,Math.min(1,(e.clientX-rect.left-8)/(rect.width-69)));if(state)draw(state.chart);});$('chart').addEventListener('pointerleave',()=>{selectedPoint=null;if(state)draw(state.chart);});
$('menu-toggle').addEventListener('click',()=>setMenu(!$('sidebar').classList.contains('open')));$('nav-backdrop').addEventListener('click',()=>setMenu(false));
$('theme-toggle').addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
window.addEventListener('hashchange',navigate);window.addEventListener('resize',()=>{if(innerWidth>800)setMenu(false);if(state)draw(state.chart);});
$('page-search').addEventListener('input',()=>{const query=$('page-search').value.trim().toLowerCase(),results=$('search-results');results.replaceChildren();results.hidden=!query;if(!query)return;for(const [name,route]of Object.entries(routes)){if(route.keywords.includes(query)||route.label.includes(query)){const link=document.createElement('a');link.href='#'+name;link.textContent=route.label;link.addEventListener('click',()=>{results.hidden=true;$('page-search').value='';});results.append(link);}}if(!results.children.length){const p=document.createElement('p');p.textContent='ไม่พบเมนูที่ค้นหา';results.append(p);}});
$('page-search').addEventListener('keydown',e=>{if(e.key==='Enter'){const link=$('search-results').querySelector('a');if(link){e.preventDefault();link.click();}}});
document.addEventListener('click',e=>{if(!e.target.closest('.quick-search'))$('search-results').hidden=true;});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const menuOpen=$('sidebar').classList.contains('open');setMenu(false);if(menuOpen)$('menu-toggle').focus();$('search-results').hidden=true;}if(e.key==='/'&&!$('login').open&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)&&getComputedStyle($('page-search').parentElement).display!=='none'){e.preventDefault();$('page-search').focus();}});
$('page-title').tabIndex=-1;text('date',new Date().toLocaleDateString('th-TH',{timeZone:'Asia/Bangkok',day:'numeric',month:'short',year:'numeric'}));
setTheme(localStorage.getItem('desk-theme')==='dark'?'dark':'light');navigate();updateControls();if(!key)$('login').showModal();else refresh();setInterval(refresh,1500);

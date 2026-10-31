# คู่มือตั้งค่า XM MT5 + Telegram + Windows VPS ทีละขั้น

เริ่มด้วยระบบจำลองในเครื่องนี้ได้ทันทีโดยไม่ต้องเติมเงิน การเชื่อม MT5 ใช้ตัว terminal ที่ล็อกอินไว้ ไม่ต้องนำรหัสบัญชี XM มาใส่ในแชตหรือ source code

## 1. ตรวจบัญชีใน XM

1. เข้าพื้นที่สมาชิก XM ผ่านเว็บ/แอปทางการที่คุณใช้อยู่
2. เปิดรายละเอียดบัญชีเทรด แล้วมองหา **Platform / MT4 / MT5**, **เลขบัญชีเทรด** และ **Server**
3. จดเลขบัญชีและชื่อเซิร์ฟเวอร์ให้ตรงทุกตัว ตัวอย่างชื่อที่แสดงอาจต่างกันตามนิติบุคคลและประเภทบัญชี อย่าเลือกจากการเดา
4. ถ้าบัญชีเดิมเป็น MT4 ให้เปิดบัญชี MT5 เพิ่มจากตัวเลือกในพื้นที่สมาชิก บอตรุ่นนี้เชื่อม MT5 เท่านั้น
5. เลือกบัญชี Demo สำหรับทดสอบวงจรส่งคำสั่งก่อน หากตัวเลือก Demo ไม่ปรากฏให้ดู help center ของพื้นที่สมาชิกคุณ เมนูและข้อเสนอของ XM ต่างกันตามประเทศ
6. ใช้ **รหัสผ่านเทรด / master password** ของบัญชีนั้นตอนล็อกอิน MT5 รหัส investor อ่านราคาได้แต่ส่งคำสั่งไม่ได้ รหัสพื้นที่สมาชิกอาจไม่ใช่รหัสบัญชีเทรด

## 2. ติดตั้งและล็อกอิน MT5

1. ดาวน์โหลด MT5 สำหรับ Windows จาก [หน้า XM MT5 ทางการ](https://www.xm.com/mt5) หรือพื้นที่สมาชิกของคุณ
2. ติดตั้งแล้วเปิด MT5
3. เลือก **File → Login to Trade Account** ใส่เลขบัญชี รหัสเทรด และ Server ที่จดไว้
4. ถ้าไม่เห็น Server ให้ใช้ **File → Open an Account** แล้วค้นหาบริษัท/เซิร์ฟเวอร์ตามที่ XM ระบุ จากนั้นเลือกล็อกอินบัญชีที่มีอยู่
5. ตรวจมุมล่างขวาว่าเชื่อมต่อแล้ว และเปิด Toolbox (Ctrl+T) แท็บ Trade ให้เห็น balance/equity
6. เปิด **View → Market Watch** หรือ Ctrl+M คลิกขวา → Show All หรือ Symbols
7. จดชื่อสินทรัพย์ **ตามที่เห็นจริง** รวม suffix เช่น `#`, `.`, `micro` ถ้ามี ชื่อ `EURUSD` ในตัวอย่างไม่จำเป็นต้องตรงกับบัญชีของคุณ
8. เปิดกราฟสินทรัพย์นั้นและเลือก timeframe **M1** รอสักครู่ให้โหลดข้อมูลแท่งย้อนหลัง (อย่างน้อย 50 แท่งปิด)

วันนี้ตามเวลาตั้งค่าเครื่องลูกข่ายคือ 31 ตุลาคม 2026 ซึ่งเป็นวันเสาร์ ตลาดหลายประเภทอาจปิด ราคาไม่อัปเดตจึงจะถูกบอตปฏิเสธ ไม่ใช่เหตุให้เพิ่มสิทธิ์หรือเปลี่ยนรหัส

## 3. อนุญาต MT5 ให้รับคำสั่งบอต

1. ไปที่ **Tools → Options → Expert Advisors**
2. เปิด **Allow algorithmic trading** (ชื่ออาจต่างเล็กน้อยตามภาษา)
3. หากมี **Disable automatic trading through the external Python API** ให้เอาเครื่องหมายออก เพื่ออนุญาต Python
4. กด OK แล้วตรวจปุ่ม **Algo Trading** บน toolbar ว่าเปิดอยู่
5. ไม่ต้องเปิด DLL imports ให้บอตนี้ และไม่ต้องลาก EA ลงกราฟ เพราะส่งผ่าน official Python API
6. เปิด MT5 ค้างไว้ตลอดเวลาที่ใช้งานบอต

อ้างอิง: [MT5 Python integration](https://www.mql5.com/en/docs/python_metatrader5), [คำสั่ง initialize](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py)

## 4. ติดตั้งตัวเชื่อม Python

เปิด PowerShell ในโฟลเดอร์ `Trading-bot` แล้วรัน:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-mt5.ps1
```

สคริปต์สร้าง `.venv` ในโปรเจกต์และติดตั้ง official `MetaTrader5` จาก PyPI หาก pip แจ้งว่าไม่มี distribution สำหรับ Python ที่ใช้ ให้ติดตั้ง Python 64-bit เวอร์ชันที่แพ็กเกจรองรับจาก python.org แล้วสร้าง .venv ด้วยเวอร์ชันนั้น ไม่ต้องใช้ package ชื่อคล้ายจากแหล่งอื่น

คัดลอกค่าตั้งต้นครั้งเดียว (ถ้ามี `.env` แล้วให้แก้ไฟล์เดิม ไม่คัดลอกทับ):

```powershell
Copy-Item .env.example .env
notepad .env
```

ถ้าเชื่อม MT5 ไม่เจอ ให้ระบุ path ของ terminal ที่ใช้อยู่ โดยคลิกขวา shortcut MT5 → Properties → Target แล้วคัดลอก path ที่ลงท้าย `terminal64.exe` เช่น:

```dotenv
MT5_PATH=C:\Program Files\XM MT5\terminal64.exe
```

ใช้ path ของเครื่องคุณจริง ไม่ใช่คัดลอกตัวอย่างโดยไม่ตรวจสอบ ถ้ามีหลาย terminal ต้องระบุ path เพื่อไม่เชื่อมผิดบัญชี

เริ่มบอตด้วย Python ใน .venv:

```powershell
.\.venv\Scripts\python.exe run.py
```

หรือ `powershell -ExecutionPolicy Bypass -File .\start.ps1` เปิด <http://127.0.0.1:8899> แล้วใช้รหัสใน `data/dashboard-token.txt` เข้าใช้งาน

ถ้าพอร์ตถูกจอง/ใช้ไปแล้ว ให้เปลี่ยน `PORT=8899` ใน `.env` เป็นพอร์ตว่าง เช่น 8901 แล้วรีสตาร์ต เปิดเว็บตามเลขใหม่ ถ้าเห็น already running ให้ใช้หน้าต่างโปรแกรมเดิมหรือหยุด process เดิมก่อน อย่าใช้ data หลายชุดเพื่อเลี่ยงล็อกแล้วเชื่อมบัญชีเดียวพร้อมกัน

## 5. ตั้งค่า dashboard สำหรับ XM Demo

1. ใน dashboard กดพักและปิดสถานะจำลองที่เปิดอยู่ก่อนเปลี่ยนค่า
2. เปลี่ยน **แหล่งการเทรด → XM / MetaTrader 5**
3. ใส่ชื่อสินทรัพย์ตาม Market Watch เลือกเพียงตัวเดียวต่อครั้ง รุ่นนี้ไม่ใช่ portfolio หลายสินทรัพย์พร้อมกัน
4. ใส่ **1 หน่วยเงินบัญชี เท่ากับกี่บาท** จากหน่วยจริงของบัญชี:
   - บัญชี THB: ใช้ 1 (ระบบใช้ 1 อัตโนมัติ)
   - บัญชี USD: ใส่จำนวนบาทต่อ 1 USD ตามอัตราที่คุณต้องการใช้ประมาณ
   - บัญชี cent: ถ้า 100 หน่วยในบัญชีเท่ากับ 1 USD และคุณใช้อัตรา 35 บาท/USD ต้องใส่ **0.35** ไม่ใช่ 35 ตัวเลขนี้เป็นตัวอย่าง ไม่ใช่อัตราแลกเปลี่ยนปัจจุบัน
5. เลือก lot ตามขั้นต่ำของ symbol นั้น เช่น 0.01 **เฉพาะเมื่อ Market Watch / Specification ระบุว่ารองรับ** ไม่ใช่ทุกสินทรัพย์ใช้ขั้นต่ำเดียวกัน
6. เลือกเป้า **จำนวนเงินบาท**, ปิดกำไร 10, ปิดขาดทุน 10 หรือตั้งเอง
7. ตั้ง daily loss ตามที่ต้องการ ค่าเริ่มต้น 100 บาท และ spread points ตาม specification ของ symbol (points ไม่ใช่ pips)
8. กดบันทึก รอประมาณ 1–2 วินาทีให้ MT5 เชื่อมต่อและแสดงบัญชี
9. ตรวจเลขบัญชี/Server/หน่วยเงิน/Demo บน dashboard แล้วกด **เริ่มบอต**
10. ดู Trade ใน MT5 คู่กันรอบแรก ต้องเห็นคำสั่งจากบอตพร้อมค่า SL และ TP ตรวจ History ตอนปิดรอบ แล้วเทียบกับ dashboard
11. ถ้าเป้า 10 บาทเล็กกว่าข้อจำกัด broker บอตจะหยุดและบอกเหตุผล ไม่ขยาย SL ให้เอง ให้ปรับ lot/เป้าผ่าน dashboard

เลือก **เปิดต่อเนื่อง** ตามที่คุณต้องการ จะเปิดรอบใหม่เมื่อระบบตรวจพบว่ารอบเดิมปิดใน poll ถัดไป โดยเลือก Buy/Sell ตาม EMA ถ้าไม่มีสัญญาณจะเลือก Buy ส่วน **เปิดเมื่อมีสัญญาณแนวโน้ม** จะยอมว่างรอได้

### เรื่องเป้าและต้นทุนที่สัมพันธ์กับทุน 1,000 บาท

ตั้งกำไรและขาดทุนเท่ากันที่ 10 บาทไม่ได้ทำให้ผลเฉลี่ยเป็นบวก หากอัตราชนะ 50% และชนะ/แพ้ได้สุทธิเท่ากัน ผลคาดหวังก่อนต้นทุนเท่ากับศูนย์ ส่วน commission, spread และ slippage จะทำให้แย่ลง การเปิดบ่อยเพิ่มจำนวนครั้งที่จ่ายต้นทุน ต้องทดสอบผลสุทธิด้วยข้อมูลตลาดจริงก่อนสรุปว่ากลยุทธ์ดี

บอตนี้ยังไม่ได้คัดเลือกกลยุทธ์ที่ทำกำไรดีที่สุด ใช้กฎ EMA ที่อ่านและตรวจสอบได้เป็นจุดเริ่มต้น เปอร์เซ็นต์เป้าคิดจากทุนที่กรอก ไม่ใช่ปรับขนาด lot อัตโนมัติ และไม่มี martingale หรือการทบ lot หลังแพ้

## 6. ตั้ง Telegram

1. เปิด Telegram ค้นหา **@BotFather** ที่เป็นบัญชีทางการ ตรวจชื่อให้ตรง
2. ส่ง `/newbot` แล้วตั้งชื่อและ username ตามขั้นตอน
3. เก็บ bot token ที่ได้ไว้ส่วนตัว ไม่ส่งมาในแชตนี้
4. เปิดแชตกับบอตที่สร้างเองแล้วกด Start หรือส่ง `/start`
5. เปิด `.env` ใส่ `TELEGRAM_BOT_TOKEN=...` แต่ยังไม่ต้องใส่ chat ID
6. หา chat ID ด้วย PowerShell ด้านล่าง สคริปต์ถาม token แบบซ่อนข้อความและแสดงเฉพาะ chat ID ไม่แสดง token ใน command history:

```powershell
$secureBotToken = Read-Host 'Telegram bot token' -AsSecureString
$botTokenCredential = [PSCredential]::new('bot', $secureBotToken)
$plainBotToken = $botTokenCredential.GetNetworkCredential().Password
try {
    $telegramUpdates = Invoke-RestMethod -Uri ('https://api.telegram.org/bot' + $plainBotToken + '/getUpdates')
    $telegramUpdates.result | ForEach-Object { $_.message.chat } | Select-Object id, type, title, first_name -Unique
} catch {
    Write-Host 'อ่าน Telegram ไม่สำเร็จ ตรวจ token และอินเทอร์เน็ต'
} finally {
    $plainBotToken = $null
    $botTokenCredential = $null
    $secureBotToken = $null
}
```

7. ใช้ `id` ของแชตส่วนตัวคุณ ใส่ `TELEGRAM_CHAT_ID=...` ใน `.env` ถ้ารายการว่างให้ส่งข้อความหาบอตอีกครั้งแล้วรันใหม่
8. หยุดบอตด้วย Ctrl+C แล้วรันใหม่ (การเปลี่ยน .env ต้องรีสตาร์ต)
9. เปิด dashboard กด **ทดสอบส่ง** ในการแจ้งเตือน ต้องเห็นข้อความใน Telegram และสถานะส่งสำเร็จเพิ่มขึ้น

ไม่มีการตั้ง webhook ของ Telegram เพราะบอตนี้ส่งอย่างเดียว คำสั่งใน Telegram ไม่สามารถเปิด/ปิดออเดอร์ได้ Queue ไม่ได้เก็บข้ามรีสตาร์ตและไม่ retry ข้อความที่ล้มเหลว ให้ตรวจสถานะใน dashboard หาก Telegram มีปัญหา การเทรดยังคงดำเนินต่อ

อ้างอิง [Telegram Bot API: getUpdates และ sendMessage](https://core.telegram.org/bots/api)

## 7. เปลี่ยนเป็นบัญชีเงินจริงเมื่อคุณพร้อม

1. พักบอตและปิดสถานะ Demo ให้เรียบร้อยก่อน
2. หยุดโปรแกรมแล้วเลือกข้อมูลแยกต่อบัญชี: ตั้ง `DATA_DIR=C:\Trading-bot\data-live` ใน `.env` เพื่อไม่ปะปนกับ Demo หรือใช้โฟลเดอร์ใหม่ที่ไม่มีสถานะค้าง
3. ล็อกอินบัญชีเงินจริงใน MT5 ให้ตรง server
4. ตั้ง `ALLOW_LIVE_TRADING=true` ใน `.env` แล้วรันใหม่ การกดเริ่มใน dashboard อย่างเดียวไม่สามารถข้ามค่านี้ได้
5. data directory ใหม่เริ่มในโหมด paper เสมอ ให้ตั้ง MT5, symbol, conversion, lot และเป้าซ้ำ แล้วตรวจเลขบัญชีบน dashboard
6. ใช้รหัส dashboard จาก data directory ใหม่หากไม่ได้กำหนด DASHBOARD_TOKEN คงที่

ค่าอนุญาตเงินจริงควบคุมการเปิดออเดอร์ ส่วนการปิดสถานะบอตที่มีอยู่ยังทำได้ เพื่อไม่ล็อกการปิดความเสี่ยง ระบบ pin บัญชีตาม `login@server` และจะไม่เปิด/ปิดบนบัญชีที่เปลี่ยนไปจากเดิมใน data ชุดเดียวกัน

## 8. ย้ายขึ้น Windows VPS

1. สร้าง Windows VPS ที่ใช้งาน MT5 desktop ได้ เลือกสเปกตามความต้องการ Windows และ MT5 ของผู้ให้บริการ (จุดเริ่มทดลองอาจใช้ 2 vCPU/4 GB RAM แต่ไม่ใช่ minimum ที่รับรอง)
2. เข้า Remote Desktop ด้วยบัญชีของคุณ แล้วติดตั้ง Python 64-bit และ XM MT5
3. คัดลอกโปรเจกต์ไป `C:\Trading-bot` ไม่คัดลอก `.venv` จากเครื่องเดิม ให้รัน `install-mt5.ps1` ใหม่
4. หากย้ายข้อมูลเดิมให้หยุดบอตเครื่องต้นทางก่อน แล้วสำรอง/คัดลอกทั้ง data directory ขณะหยุดโปรแกรม เพื่อให้ SQLite กับสถานะสอดคล้องกัน ห้ามรันบอตสองเครื่องกับบัญชีเดียว
5. ใส่ `.env` บน VPS, ล็อกอิน MT5, เปิด Algo Trading แล้วรัน `start.ps1`
6. เปิด dashboard ผ่าน browser บน Remote Desktop ได้ทันทีโดยใช้ localhost ไม่ต้องเปิดพอร์ต 8899 ออกสาธารณะ
7. ปิด sleep/hibernate และตั้ง Windows Update ให้ไม่รีสตาร์ตกลางช่วงที่ตั้งใจเทรด ตรวจนโยบายผู้ให้บริการเรื่อง session ที่ disconnect
8. ออกจาก Remote Desktop ด้วย **Disconnect** โดยไม่ Sign out เพราะ Sign out จะปิด MT5 desktop ของ session

### เริ่มโปรแกรมเมื่อล็อกอินและรีสตาร์ตเมื่อเกิดปัญหา

เปิด Task Scheduler → Create Task:

- General: ตั้งชื่อ Trading Desk, เลือกผู้ใช้ที่ล็อกอิน MT5 และ **Run only when user is logged on** เพื่อให้ใช้ desktop session เดียวกัน
- Triggers: At log on ของผู้ใช้นั้น Delay 1 minute ให้ MT5 พร้อมก่อน
- Actions: Start a program → `C:\Trading-bot\.venv\Scripts\python.exe`
- Add arguments: `C:\Trading-bot\run.py`
- Start in: `C:\Trading-bot`
- Settings: Restart task every 1 minute, กำหนดจำนวนครั้งตามต้องการ; If already running → Do not start a new instance; ปิดเงื่อนไข Stop after 3 days ถ้ามี

สร้าง shortcut ของ MT5 ใน Startup ของผู้ใช้ (Win+R → `shell:startup`) หากต้องการเปิด terminal เมื่อล็อกอิน ระบบไม่ได้ auto-login Windows หลัง reboot ดังนั้นการเปิดเครื่องใหม่ต้องให้ผู้ใช้เข้าสู่ session ก่อน และบอตจะ **พักออเดอร์ใหม่ทุกครั้งหลังเริ่ม process** คุณต้องตรวจสถานะและกดเริ่มอีกครั้ง การตั้งให้เปิดเทรดต่ออัตโนมัติหลัง reboot ยังไม่มีในรุ่นนี้

### เปิด dashboard จากอุปกรณ์อื่น

วิธีเริ่มต้นที่เรียบง่ายคือใช้ Remote Desktop หรือ SSH tunnel ถ้า VPS เปิด OpenSSH อยู่แล้ว:

```text
ssh -L 8899:127.0.0.1:8899 your-user@your-vps
```

จากนั้นเปิด localhost:8899 บนเครื่องคุณ หากต้องการโดเมนสาธารณะ ให้ติดตั้ง reverse proxy ที่รองรับ HTTPS (เช่น Caddy/IIS), จำกัดการเข้าถึง และให้ proxy ส่งต่อไป localhost:8899 โดยคง Authorization header ห้ามเปิด Python HTTP server นี้รับอินเทอร์เน็ตโดยตรง หรือส่ง dashboard token ผ่าน HTTP ที่ไม่เข้ารหัส

## 9. ถ้าติดปัญหา

| อาการ | จุดตรวจ |
|---|---|
| เปิดเว็บไม่ได้ | run.py ยังทำงานหรือไม่, พอร์ตใน .env ตรง URL หรือไม่ |
| รหัส dashboard ผิด | ใช้ไฟล์ dashboard-token.txt ของ DATA_DIR ที่ใช้งานจริง หรือ DASHBOARD_TOKEN ถ้าตั้งเอง |
| เชื่อม MT5 ไม่สำเร็จ | terminal64.exe path, login/server, การเชื่อมต่อมุมล่างขวา |
| ราคาเก่า | ตลาดปิด, symbol ไม่อัปเดต, เน็ตหลุด; ทดลองตลาดเปิดโดยไม่ฝืนส่งคำสั่ง |
| ไม่พบ symbol | คัดลอกชื่อพร้อม suffix จาก Market Watch |
| คำสั่งถูกปฏิเสธ | ดูข้อความบน dashboard, MT5 Journal, lot, margin, Algo Trading, spread, stops ขั้นต่ำ |
| ผลส่งไม่ชัดเจน | ตรวจ Trade, History และ Journal ใน MT5 ก่อนกดเริ่มใหม่ บอตไม่ retry เอง |
| มีสถานะแต่ไม่มี SL/TP | ตรวจและแก้/ปิดที่ MT5 ก่อน ระบบหยุดเปิดรอบใหม่ |
| กรอก conversion แล้วแก้ไม่ได้ | พักและปิดสถานะก่อน ตรวจว่า MT5 ยังเชื่อมต่อเพื่อยืนยันสถานะ |
| account identity changed | กลับบัญชีเดิม หรือใช้ DATA_DIR แยกหลังจัดการสถานะเดิมแล้ว |
| Telegram ส่งไม่ได้ | chat ได้กด Start หรือยัง, token/chat ID, อินเทอร์เน็ต, รีสตาร์ตหลังแก้ .env |

เก็บ `.env`, data directory และ backup ไว้ส่วนตัว หากต้องส่ง log เพื่อแก้ปัญหาให้ตัด token รหัสผ่านและข้อมูลบัญชีก่อน

# Trading Desk

บอต Python สำหรับ XM MT5 พร้อม dashboard ภาษาไทย, Telegram และ SQLite
เขียนใหม่ในโปรเจกต์นี้ ไม่ได้คัดลอกกลยุทธ์ที่อ้างผลกำไรจาก GitHub

Dashboard ออกแบบใหม่ตามแนวทาง [Horizon UI](https://github.com/horizon-ui/horizon-tailwind-react): แยกหน้าภาพรวม, ตั้งค่าบอต, ประวัติ, แจ้งเตือน และเชื่อมบัญชี มีโหมดสว่าง/มืด เมนูมือถือ และค้นหาประวัติ ดูรายละเอียดและใบอนุญาตใน [UI redesign](docs/UI-REDESIGN.md) หากอัปเดตจากหน้าเดิม ให้หยุดโปรแกรมด้วย Ctrl+C แล้วรันใหม่หนึ่งครั้งเพื่อโหลดเส้นทางฟอนต์ใหม่ จากนั้นกด Ctrl+F5 ในเบราว์เซอร์

## เริ่มทดลองตอนนี้

ต้องมี Python 64-bit (เครื่องนี้มี Python 3.13 แล้ว) โหมดจำลองไม่ต้องติดตั้ง package เพิ่ม

เปิด PowerShell ในโฟลเดอร์นี้:

```powershell
python run.py
```

1. เปิด <http://127.0.0.1:8899>
2. เปิดไฟล์ `data/dashboard-token.txt` ด้วย Notepad แล้วคัดลอกรหัสไปใส่หน้าเข้าใช้งาน
3. คงโหมด **จำลอง** แล้วกด **เริ่มบอต**
4. เป้าเริ่มต้น +10 / −10 บาทต่อรอบ ทุนจำลองเริ่ม 1,000 บาท เปิดต่อเนื่องทีละ 1 สถานะ
5. **พักเปิดออเดอร์** หยุดรอบใหม่แต่ยังเฝ้า SL/TP ของสถานะเดิม ส่วน **ปิดสถานะและพัก** ปิดสถานะด้วยราคาตลาด

โหมดจำลองใช้ราคาสุ่มสังเคราะห์และต้นทุน spread จำลอง ไม่ใช่ราคาตลาด ไม่ใช่ backtest และใช้ประเมินกำไรของกลยุทธ์ไม่ได้ ตัวเลือก symbol ในโหมดนี้เป็นป้ายกำกับตลาดทดสอบเท่านั้น

**คู่มือทีละขั้น:** [ติดตั้ง XM MT5, Telegram และ Windows VPS](docs/SETUP-TH.md)

## สิ่งที่ทำได้

- เป้าแบบเงินบาทคงที่ หรือ % ของทุนที่กำหนด; lot และขีดจำกัดขาดทุนรายวันตั้งเอง
- เปิดรอบใหม่ในรอบประมวลผลที่พบว่ารอบเก่าปิด (MT5 poll ทุกประมาณ 1 วินาที ไม่ใช่ execution แบบไร้ latency)
- เลือกเปิดต่อเนื่องหรือรอสัญญาณ EMA12/EMA26; ถ้าโหมดต่อเนื่องไม่มีสัญญาณจะเลือก Buy
- MT5 วิเคราะห์จาก 120 แท่ง M1 ที่ปิดแล้ว (ต้องมีอย่างน้อย 50 แท่ง); กรองระยะ EMA ด้วยค่าเฉลี่ยการเปลี่ยนแปลงราคาปิด ไม่ใช่ AI/LLM และไม่ใช่ ATR
- ตั้ง symbol ได้จากรายการบัญชีจริง: forex, โลหะ, indices หรือหุ้น/CFD ที่บัญชี XM นั้นรองรับ
- กราฟราคา, สถานะ, กำไร/ขาดทุน, ประวัติ 100 รายการล่าสุดของโหมดนั้น, export CSV, event log
- แจ้ง Telegram เมื่อเริ่ม/พัก, เปิด/ปิด, เกิดข้อผิดพลาด, ถึงขีดจำกัด และสรุปทุกชั่วโมงที่ worker ทำงานปกติ
- เก็บสถานะลง SQLite; หลังรีสตาร์ตพักรอบใหม่และกลับมาเฝ้าสถานะที่ค้างอยู่
- MT5 ส่ง SL/TP ไปโบรกเกอร์พร้อมคำสั่งเปิด; ตรวจ lot, margin, spread, ความสดราคา และสถานะที่มีอยู่ก่อนส่ง
- ไม่ส่งคำสั่งซ้ำอัตโนมัติเมื่อผล broker คลุมเครือ; หนึ่ง process ต่อ DATA_DIR; ใช้บัญชีเดียว/บอตเดียวต่อ MT5 terminal

## ข้อจำกัดที่ต้องรู้ก่อนเชื่อมเงินจริง

เป้า +10 / −10 บาทไม่ใช่คำรับประกันผลสุทธิ ราคาปิดจริงมี spread, commission, swap, gap, slippage และ tick rounding บอตคำนวณ SL/TP จากกำไรขาดทุนของราคาโดยประมาณ ไม่รวมค่าธรรมเนียมล่วงหน้า

อัตรา `account_to_thb` กรอกเอง ไม่ดึง FX อัตโนมัติ ตัวอย่าง 1 USD = 35 THB ใช้เพื่ออธิบายการตั้งค่าเท่านั้น ไม่ใช่อัตราปัจจุบัน หากเป็นบัญชี cent ต้องใช้อัตราต่อ cent ประวัติที่นำเข้าจะถูกเก็บด้วยอัตรา ณ เวลานำเข้า ไม่ใช่อัตราย้อนหลัง แนะนำคงอัตราเดิมระหว่างวันและใช้เพื่อประมาณผลเป็นบาท

ทุนที่กำหนดใช้คำนวณเป้า % เท่านั้น ไม่ได้จำกัดยอด margin ของบัญชีจริง ขีดจำกัดรายวัน MT5 คิดจากการเปลี่ยนแปลง equity ทั้งบัญชีตั้งแต่บอตเริ่มติดตามในวันกรุงเทพฯ จึงรวมธุรกรรมอื่นและเงินฝากถอน ไม่ใช่ P/L ที่แยกเฉพาะบอต ถึงขีดจำกัดแล้วพักออเดอร์ใหม่ สถานะเดิมยังใช้ SL/TP เดิม

MT5 ต้องเปิดและล็อกอินตลอด ปิดโปรแกรมนี้จะหยุดติดตามและหยุด Telegram แต่ SL/TP ที่ broker รับไว้ยังอยู่ ไม่ใช่การป้องกัน gap หรือการปิดที่ราคาเป๊ะ และระบบแจ้งเตือนนี้ไม่ใช่ external watchdog หาก VPS ดับ Telegram จาก VPS จะส่งไม่ได้

ยังไม่ได้พิสูจน์ความสามารถทำกำไร, ทดสอบบัญชี XM จริง, backtest หรือ forward test กับตลาดจริง ชุด unit tests ใช้ simulation และ MT5 test doubles เท่านั้น ใช้ XM Demo ตรวจวงจรการส่งจริงก่อน การเพิ่มความถี่อย่างเดียวไม่ได้เพิ่มความได้เปรียบและเพิ่มต้นทุนต่อรอบ

## โครงสร้างและการทดสอบ

```text
run.py            เริ่มโปรแกรมและ worker, ล็อก process, โหลด .env
bot/engine.py     กติกา, paper, persistence, daily limits
bot/mt5.py        ตัวเชื่อม official MetaTrader5 Python API
bot/server.py     HTTP API ที่ต้องใช้ bearer token
bot/notify.py     Telegram queue แยกจาก trading worker
web/              Dashboard ไม่พึ่ง CDN
tests/            Unit tests และ HTTP integration tests
data/             ฐานข้อมูลและรหัสเข้า dashboard (ไม่ควรเผยแพร่)
```

```powershell
python -m unittest discover -s tests -v
python -m compileall -q bot run.py
node --check web/app.js
```

API ใช้ `Authorization: Bearer <dashboard-token>` และ JSON: `GET /api/state`, `GET /api/symbols`, `POST /api/settings`, `/api/start`, `/api/pause`, `/api/flatten`, `/api/test-alert` รันผูก localhost เป็นค่าเริ่มต้น ไม่เปิดออกอินเทอร์เน็ตโดยตรง

## เอกสารอ้างอิง

- [XM MT5 และ Expert Advisors](https://www.xm.com/mt5)
- [Official MT5 Python integration](https://www.mql5.com/en/docs/python_metatrader5)
- [MT5 order_send และ SL/TP](https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py)
- [MT5 order_calc_profit ใช้หน่วยเงินบัญชี](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py)
- [Telegram Bot API](https://core.telegram.org/bots/api)

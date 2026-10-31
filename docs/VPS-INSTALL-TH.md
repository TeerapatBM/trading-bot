# ติดตั้งบน Windows Server 2025

แพ็ก `TradingDesk-Windows-VPS.zip` เตรียมไว้สำหรับเครื่อง VPS เป้าหมาย ไม่ใช่เครื่องที่ใช้พัฒนา โปรเจกต์นี้ยังไม่ได้ติดตั้งลง VPS จนกว่าจะรัน installer และตรวจ deployment-report.json บนเครื่องนั้นสำเร็จ

## เริ่มติดตั้ง

1. คัดลอก ZIP ไป VPS และแตกไฟล์เป็นโฟลเดอร์ เช่น `C:\TradingDesk-Installer`
2. เปิด `INSTALL-VPS.cmd` แล้วอนุญาต Administrator หาก Windows แสดง UAC
3. รอการติดตั้งจบ และเปิด shortcut **Trading Desk** บน Desktop
4. เปิด shortcut **Trading Desk - dashboard key** เพื่อดูรหัสเข้า dashboard
5. ล็อกอินบัญชี XM ใน MT5 ด้วยตัวเอง จากนั้นตั้งบัญชี/สินทรัพย์ในหน้า **ตั้งค่าบอต**

หากเปิด PowerShell แบบ Administrator อยู่แล้ว รันคำสั่งนี้จากโฟลเดอร์ที่แตก ZIP:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\deploy\install-vps.ps1
```

ค่าเริ่มต้น: `C:\Trading-bot`, `https://btxm.sysplatsec.dev`, backend `127.0.0.1:8899`, MT5 `C:\Program Files\TradingDesk MT5` เปลี่ยน path/โดเมนได้ผ่านพารามิเตอร์ของ install-vps.ps1

## Installer ทำอะไร

- ตรวจ hash ทุกไฟล์ในแพ็ก และลายเซ็น Python / MT5 ก่อนติดตั้ง
- ติดตั้ง Python 3.13.17 x64 แบบ dedicated runtime โดยไม่เปลี่ยน PATH ของระบบ
- สร้าง .venv และติดตั้ง official MetaTrader5 connector พร้อม numpy จาก wheel ในแพ็ก
- ติดตั้ง MT5 ตัวทางการของ MetaQuotes แบบ `/auto` ใช้ค้นหาเซิร์ฟเวอร์ XM และล็อกอินบัญชีของคุณได้
- MT5 setup ยังต้องใช้อินเทอร์เน็ตเพื่อดาวน์โหลดส่วนประกอบ ส่วน Python installer, Caddy และ Python wheels รวมไว้ในแพ็กแล้ว
- คัดลอก dashboard เวอร์ชัน Horizon UI พร้อมฟอนต์ในเครื่อง
- สร้าง `.env` ใหม่โดยตั้ง `ALLOW_LIVE_TRADING=false`; เริ่มในโหมดจำลองและพักบอต
- ตั้ง Scheduled Tasks **TradingDesk-MT5** และ **TradingDesk-Worker** ให้ทำงานใน desktop session ของผู้ติดตั้งเมื่อล็อกอิน และกู้ worker เมื่อ crash
- ติดตั้ง Caddy เป็น Windows Service **TradingDeskProxy**, ออกใบรับรอง HTTPS และ proxy มาที่ localhost
- เพิ่ม Firewall เฉพาะ TCP 80/443 สำหรับ Caddy ไม่เปิด backend 8899 และไม่เปลี่ยน RDP/SSH/WinRM
- สร้าง shortcut บน Desktop และ `deployment-report.json` ที่ไม่มีรหัสผ่าน

แพ็กไม่รวมรหัสผ่าน VPS, บัญชี XM, token Telegram, รหัส dashboard หรือฐานข้อมูลจากเครื่องพัฒนา รหัส dashboard จะสร้างใหม่บน VPS

## DNS / Cloudflare

ตั้ง A record `btxm.sysplatsec.dev` → `119.10.138.141` เป็น DNS only ในตอนออกใบรับรอง ผู้ให้บริการ VPS ต้องอนุญาต inbound TCP 80 และ 443 ด้วย Caddy ออก/ต่อใบรับรองอัตโนมัติ หากใช้ Cloudflare proxy ภายหลังให้ใช้ SSL/TLS **Full (strict)** หลังตรวจว่า origin HTTPS ใช้ได้แล้ว

ผลตรวจ DNS จากเครื่องพัฒนาในวันที่ 31 ตุลาคม 2026 ชี้ IP ตามนี้แล้ว แต่ยังไม่ได้ยืนยัน HTTPS ของแอปบน VPS

## สิ่งที่เจ้าของต้องทำใน MT5

1. File → Login to Trade Account หรือ Open an Account → ค้นหาโบรกเกอร์/Server ของ XM
2. ใช้เลขบัญชี รหัสเทรด และ Server ของคุณ
3. เปิด Algo Trading และอนุญาต external Python API ใน Tools → Options → Expert Advisors
4. เปิด Market Watch และกราฟ M1 ของ symbol ที่ต้องการให้มีข้อมูลย้อนหลังอย่างน้อย 50 แท่ง
5. ใน dashboard เลือก XM / MT5, symbol, lot และอัตราแปลง THB แล้วบันทึก

Installer ไม่สร้าง/ล็อกอินบัญชี XM และไม่เปิดออเดอร์จริง หลัง reboot ต้องล็อกอิน Windows ก่อนเพื่อให้ MT5 และ worker ทำงานใน interactive session เดียวกัน ระบบไม่เก็บรหัส Administrator สำหรับ auto-login และหลังเริ่ม process บอตจะพักรอบใหม่เสมอ

## ตรวจผล

```powershell
Get-Service TradingDeskProxy
Get-ScheduledTask -TaskName TradingDesk-Worker,TradingDesk-MT5
Get-Content C:\Trading-bot\deployment-report.json
Invoke-WebRequest https://btxm.sysplatsec.dev/ -UseBasicParsing
```

ต้องเห็น localDashboardHealthy=true, mode=paper, running=false และ httpsVerified=true จึงถือว่ารอบติดตั้ง/HTTPS ตรวจสำเร็จ หาก HTTPS pending ให้ตรวจ DNS, firewall ของผู้ให้บริการ และ `C:\Trading-bot\logs\caddy-runtime.log` โดย Caddy จะลองออก certificate ใหม่เอง

Installer หยุดโดยไม่ปิดแอปอื่น หากพอร์ต 80/443/8899 ถูกใช้อยู่ หรือพบ installation/task/service เดิม การอัปเดตระบบที่มีการเทรดอยู่ต้องทำเป็นขั้นตอนแยก ไม่เขียนทับอัตโนมัติ

## แหล่งติดตั้ง

- [Python 3.13.17](https://www.python.org/downloads/release/python-31317/) — Windows installer พร้อม SHA256 จากหน้า release
- [MetaTrader 5 ทางการ](https://www.metatrader5.com/en/download), [การติดตั้ง /auto](https://www.metatrader5.com/en/terminal/help/start_advanced/installation)
- [MetaTrader5 Python connector](https://pypi.org/project/MetaTrader5/)
- [Caddy releases](https://github.com/caddyserver/caddy/releases), [Windows service](https://caddyserver.com/docs/running#windows-service)

## สถานะการเข้าถึงจากเซสชันพัฒนา

ตรวจ TCP พบพอร์ต 3389 รับการเชื่อมต่อ ขณะที่ SSH 22 และ WinRM 5985/5986 ใช้งานไม่ได้ เครื่องมือควบคุมหน้าจอของเซสชันนี้เริ่มไม่ได้ (`failed to write kernel assets`) จึงยังไม่ได้ล็อกอินหรือเปลี่ยนแปลง VPS การมี ZIP และผล unit tests ไม่ใช่หลักฐานว่าติดตั้งบน VPS แล้ว

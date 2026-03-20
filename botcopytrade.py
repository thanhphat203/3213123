import asyncio
import requests
from playwright.async_api import async_playwright

# ==========================================
# 1. CẤU HÌNH
# ==========================================
TG_TOKEN  = "8133411049:AAGQfgj1Ja2ObN4TjsNIbs1vXFweuCbqcLs"
TG_CHAT   = "-1003631553178" # Nhớ thêm -100 nếu là Supergroup

# Danh sách cá mập cần theo dõi
TARGET_USERS = ["WEEX_T0mmy", "WEEX_Mr0"]

# Bộ nhớ lưu các lệnh đã báo
seen_trades = set()

# ==========================================
# 2. HÀM GỬI TELEGRAM (Giao diện Tối giản)
# ==========================================
def send_telegram(text: str):
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        if response.status_code != 200:
            print(f"Lỗi từ Telegram: {response.text}")
    except Exception as e:
        print(f"Lỗi đường truyền Telegram: {e}")

# ==========================================
# 3. LÕI PLAYWRIGHT - QUÉT TOÀN SÀN
# ==========================================
async def scan_event(context, event_url, event_title):
    global seen_trades
    page = await context.new_page()
    
    try:
        await page.goto(event_url, wait_until="networkidle", timeout=15000)
        
        # Click vào tab Hoạt động
        try:
            await page.get_by_text("Hoạt động", exact=True).click(timeout=3000)
            await page.wait_for_timeout(1500)
        except:
            pass 

        for target in TARGET_USERS:
            elements = await page.get_by_text(target).element_handles()
            
            for el in elements:
                try:
                    # Lấy text khối giao dịch
                    parent = await el.evaluate_handle("node => node.parentElement.parentElement")
                    raw_text = await parent.inner_text()
                    
                    if raw_text and target in raw_text:
                        # Tách dòng để lấy dữ liệu
                        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                        
                        user = lines[0] if len(lines) > 0 else target
                        selection = lines[2] if len(lines) > 2 else "Không rõ"
                        
                        # Tìm dòng chứa số tiền
                        amount = "Không rõ"
                        for line in lines:
                            if "$" in line:
                                amount = line
                                break
                        
                        # TẠO ID DUY NHẤT (Bỏ qua thời gian để không bị báo trùng)
                        stable_string = f"{event_url}_{user}_{selection}_{amount}"
                        trade_id = hash(stable_string)
                        
                        if trade_id not in seen_trades:
                            seen_trades.add(trade_id)
                            
                            # GIAO DIỆN TELEGRAM TỐI GIẢN
                            msg = (
                                f"🔔 <b>LỆNH MỚI</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"👤 <b>Trader:</b> <code>{user}</code>\n"
                                f"📌 <b>Sự kiện:</b> {event_title}\n"
                                f"🎯 <b>Vào kèo:</b> <b>{selection}</b>\n"
                                f"💵 <b>Volume:</b> <b>{amount}</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                            )
                            print(f"[+] Bắt được lệnh: {user} -> {selection} ({amount})")
                            send_telegram(msg)
                            
                except Exception as e:
                    print(f"Lỗi đọc phần tử của {target}: {e}")
                    
    except Exception as e:
        print(f"Lỗi tải trang sự kiện: {event_title}")
    finally:
        await page.close()

async def run_radar():
    print("Khởi động Radar Quét Toàn Sàn...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
        )
        
        while True:
            try:
                print("\n🔄 Đang lấy danh sách 20 sự kiện top volume...")
                api_url = "https://api.everyx.io/events/v2?limit=20&status=open&sortby=24 hours trading volume"
                response = requests.get(api_url, timeout=10)
                
                if response.status_code == 200:
                    events = response.json().get('data', [])
                    
                    if not events:
                        await asyncio.sleep(10)
                        continue
                        
                    print(f"📍 Đang quét {len(events)} sự kiện...")
                    
                    for ev in events:
                        event_id = ev.get('code') or ev.get('_id')
                        event_title = ev.get('title') or ev.get('name', 'Sự kiện không tên')
                        
                        if event_id:
                            event_url = f"https://everyx.io/events/{event_id}"
                            await scan_event(context, event_url, event_title)
                            
            except Exception as e:
                print(f"Lỗi vòng lặp chính: {e}")
            
            print("⏳ Hoàn thành 1 chu kỳ. Nghỉ 5 giây...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(run_radar())
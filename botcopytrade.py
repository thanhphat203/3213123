import asyncio
import requests
import os
import json
from playwright.async_api import async_playwright

# ==========================================
# 1. CẤU HÌNH BẢO MẬT TỪ GITHUB SECRETS
# ==========================================
TG_TOKEN  = os.environ.get("TG_TOKEN")
TG_CHAT   = os.environ.get("TG_CHAT")
TARGET_USERS = ["WEEX_T0mmy", "WEEX_Mr0"]

# ==========================================
# 2. HỆ THỐNG TRÍ NHỚ (Chống báo trùng khi chạy lại)
# ==========================================
STATE_FILE = "seen_trades.json"

# Nạp trí nhớ cũ
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        seen_trades = set(json.load(f))
else:
    seen_trades = set()

def send_telegram(text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        print(f"Lỗi gửi Telegram: {e}")

# ==========================================
# 3. LÕI PLAYWRIGHT
# ==========================================
async def scan_event(context, event_url, event_title):
    global seen_trades
    page = await context.new_page()
    
    try:
        await page.goto(event_url, wait_until="networkidle", timeout=15000)
        try:
            await page.get_by_text("Hoạt động", exact=True).click(timeout=3000)
            await page.wait_for_timeout(1500)
        except:
            pass 

        for target in TARGET_USERS:
            elements = await page.get_by_text(target).element_handles()
            for el in elements:
                try:
                    parent = await el.evaluate_handle("node => node.parentElement.parentElement")
                    raw_text = await parent.inner_text()
                    
                    if raw_text and target in raw_text:
                        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                        user = lines[0] if len(lines) > 0 else target
                        selection = lines[2] if len(lines) > 2 else "Không rõ"
                        
                        amount = "Không rõ"
                        for line in lines:
                            if "$" in line:
                                amount = line
                                break
                        
                        stable_string = f"{event_url}_{user}_{selection}_{amount}"
                        trade_id = hash(stable_string)
                        
                        if trade_id not in seen_trades:
                            seen_trades.add(trade_id)
                            msg = (
                                f"🔔 <b>LỆNH MỚI</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                                f"👤 <b>Trader:</b> <code>{user}</code>\n"
                                f"📌 <b>Sự kiện:</b> {event_title}\n"
                                f"🎯 <b>Vào kèo:</b> <b>{selection}</b>\n"
                                f"💵 <b>Volume:</b> <b>{amount}</b>\n"
                                f"━━━━━━━━━━━━━━━━━━\n"
                            )
                            print(f"[+] Bắt được lệnh: {user} -> {selection}")
                            send_telegram(msg)
                except Exception as e:
                    pass
    except Exception as e:
        pass
    finally:
        await page.close()

async def run_radar():
    print("🚀 Bắt đầu quét một lượt toàn sàn...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True) 
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"
        )
        
        try:
            api_url = "https://api.everyx.io/events/v2?limit=20&status=open&sortby=24 hours trading volume"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                events = response.json().get('data', [])
                print(f"📍 Đang quét {len(events)} sự kiện top volume...")
                
                for ev in events:
                    event_id = ev.get('code') or ev.get('_id')
                    event_title = ev.get('title') or ev.get('name', 'Sự kiện không tên')
                    if event_id:
                        await scan_event(context, f"https://everyx.io/events/{event_id}", event_title)
        except Exception as e:
            print(f"Lỗi API: {e}")
            
    # LƯU LẠI TRÍ NHỚ TRƯỚC KHI TẮT BOT
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen_trades), f)
    print("✅ Hoàn thành quét. Đã lưu trí nhớ và tự động tắt.")

if __name__ == "__main__":
    asyncio.run(run_radar())

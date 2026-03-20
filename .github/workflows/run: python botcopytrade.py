name: EveryX Radar Bot

on:
  schedule:
    - cron: '*/5 * * * *' # Cứ 5 phút chạy 1 lần
  workflow_dispatch: # Cho phép bấm chạy bằng tay để test

jobs:
  run-bot:
    runs-on: ubuntu-latest

    permissions:
      contents: write # Cấp quyền để bot ghi file trí nhớ ngược lên GitHub

    steps:
      - name: Lấy code về máy chủ
        uses: actions/checkout@v3

      - name: Cài đặt Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Cài đặt thư viện & Trình duyệt Playwright
        run: |
          pip install requests playwright
          playwright install chromium

      - name: 🚀 Bắt đầu quét Sàn
        env:
          TG_TOKEN: ${{ secrets.TG_TOKEN }}
          TG_CHAT: ${{ secrets.TG_CHAT }}
        run: python bot.py

      - name: 💾 Lưu trí nhớ vào GitHub
        run: |
          git config --global user.name "github-actions[bot]"
          git config --global user.email "github-actions[bot]@users.noreply.github.com"
          git add seen_trades.json
          # Chỉ commit nếu có lệnh mới làm file thay đổi
          git diff --quiet && git diff --staged --quiet || git commit -m "Auto-update seen trades"
          git push

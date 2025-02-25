#!/usr/bin/env python3
import asyncio
from requests_html import AsyncHTMLSession
from bs4 import BeautifulSoup
import re
from prettytable import PrettyTable
from tqdm import tqdm
import pandas as pd

def shorten_pubkey(pubkey, max_length=30):
    if len(pubkey) > max_length:
        return pubkey[:10] + "..." + pubkey[-10:]
    return pubkey

async def fetch_pubkey_data(pubkey, session):
    url = f"https://testnet.popstats.hemi.network/pubkey/{pubkey}.html"
    try:
        r = await session.get(url)
        await r.html.arender(wait=3, sleep=2)
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return None

    soup = BeautifulSoup(r.html.html, "html.parser")

    # Извлечение Total Testnet Season PoP Mining Points:
    total_points = None
    for h2 in soup.find_all("h2"):
        if "Total Testnet Season PoP Mining Points:" in h2.get_text():
            font_tag = h2.find("font")
            if font_tag:
                total_points = font_tag.get_text(strip=True)
            else:
                m = re.search(r"Total Testnet Season PoP Mining Points:\s*(\d+)", h2.get_text())
                if m:
                    total_points = m.group(1)
            break

    summary_data = None
    summary_h2 = soup.find(lambda tag: tag.name == "h2" and "PoP Points Summary:" in tag.get_text())
    if summary_h2:
        table_tag = summary_h2.find_next("table")
        if table_tag:
            rows = table_tag.find_all("tr")
            if len(rows) >= 2:
                cells = rows[1].find_all("td")
                summary_data = "\t".join(cell.get_text(strip=True) for cell in cells)
    return total_points, summary_data

async def main():
    try:
        with open("pubkey.txt", "r") as f:
            pubkeys = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Файл pubkey.txt не найден!")
        return

    session = AsyncHTMLSession()

    table = PrettyTable()
    table.field_names = [
        "Pubkey",
        "Total Points",
        "First Day Active",
        "Total Days Active",
        "Total Daily Points",
        "Total Bonus Points",
        "Ranking"
    ]
    table.max_width["Pubkey"] = 30

    results = []

    for pubkey in tqdm(pubkeys, desc="Обработка pubkeys"):
        try:
            data = await asyncio.wait_for(fetch_pubkey_data(pubkey, session), timeout=10)
        except asyncio.TimeoutError:
            print(f"Тайм-аут при обработке {pubkey}")
            data = None

        if data:
            total_points, summary_data = data
            if summary_data:
                parts = summary_data.split("\t")
                if len(parts) >= 5:
                    first_day, total_days, daily_points, bonus_points, ranking = parts[:5]
                else:
                    first_day = total_days = daily_points = bonus_points = ranking = "N/A"
            else:
                first_day = total_days = daily_points = bonus_points = ranking = "N/A"
            display_total = total_points if total_points else "не удалось спарсить"
            table.add_row([shorten_pubkey(pubkey), display_total, first_day, total_days, daily_points, bonus_points, ranking])
            results.append({
                "Pubkey": pubkey,
                "Total Points": display_total,
                "First Day Active": first_day,
                "Total Days Active": total_days,
                "Total Daily Points": daily_points,
                "Total Bonus Points": bonus_points,
                "Ranking": ranking
            })
        else:
            table.add_row([shorten_pubkey(pubkey), "не удалось спарсить",
                           "не удалось спарсить", "не удалось спарсить",
                           "не удалось спарсить", "не удалось спарсить", "не удалось спарсить"])
            results.append({
                "Pubkey": pubkey,
                "Total Points": "не удалось спарсить",
                "First Day Active": "не удалось спарсить",
                "Total Days Active": "не удалось спарсить",
                "Total Daily Points": "не удалось спарсить",
                "Total Bonus Points": "не удалось спарсить",
                "Ranking": "не удалось спарсить"
            })

    print(table)

    await session.close()

    df = pd.DataFrame(results)
    output_file = "popstats_results.xlsx"
    df.to_excel(output_file, index=False)
    print(f"\n✅ Данные сохранены в '{output_file}'")

if __name__ == "__main__":
    asyncio.run(main())

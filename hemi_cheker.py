#!/usr/bin/env python3
from requests_html import HTMLSession
from bs4 import BeautifulSoup
import re
from prettytable import PrettyTable
from tqdm import tqdm

def fetch_pubkey_data(pubkey):
    url = f"https://testnet.popstats.hemi.network/pubkey/{pubkey}.html"
    session = HTMLSession()
    try:
        r = session.get(url)
        r.html.render(wait=3, sleep=1)
    except Exception as e:
        print(f"Ошибка при загрузке {url}: {e}")
        return None

    soup = BeautifulSoup(r.html.html, "html.parser")

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

def shorten_pubkey(pubkey, max_length=30):
    if len(pubkey) > max_length:
        return pubkey[:10] + "..." + pubkey[-10:]
    return pubkey

def main():
    try:
        with open("pubkey.txt", "r") as f:
            pubkeys = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("Файл pubkey.txt не найден!")
        return

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

    for pubkey in tqdm(pubkeys, desc="Обработка pubkeys"):
        data = fetch_pubkey_data(pubkey)
        if data:
            total_points, summary_data = data
            if summary_data:
                parts = summary_data.split("\t")
                if len(parts) >= 5:
                    first_day = parts[0]
                    total_days = parts[1]
                    daily_points = parts[2]
                    bonus_points = parts[3]
                    ranking = parts[4]
                else:
                    first_day = total_days = daily_points = bonus_points = ranking = "N/A"
            else:
                first_day = total_days = daily_points = bonus_points = ranking = "N/A"
            table.add_row([shorten_pubkey(pubkey), total_points, first_day, total_days, daily_points, bonus_points, ranking])
        else:
            table.add_row([shorten_pubkey(pubkey), "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"])

    print(table)

if __name__ == "__main__":
    main()

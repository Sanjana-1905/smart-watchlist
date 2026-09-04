"""
One-time script: pulls ~40 trading days of history for seed stocks from yfinance
and saves to backend/fixtures/market_history.json.
Run manually: python scripts/fetch_fixture.py
Never called automatically — seed.py reads the committed JSON, not live yfinance.
"""
import yfinance as yf
import json
from pathlib import Path

STOCKS = [
    ("RELIANCE", "RELIANCE.NS", "Reliance Industries", "NSE", "Energy"),
    ("TCS", "TCS.NS", "Tata Consultancy Services", "NSE", "IT"),
    ("INFY", "INFY.NS", "Infosys", "NSE", "IT"),
    ("HDFCBANK", "HDFCBANK.NS", "HDFC Bank", "NSE", "Banking"),
    ("ICICIBANK", "ICICIBANK.NS", "ICICI Bank", "NSE", "Banking"),
    ("SBIN", "SBIN.NS", "State Bank of India", "NSE", "Banking"),
    ("BHARTIARTL", "BHARTIARTL.NS", "Bharti Airtel", "NSE", "Telecom"),
    ("ITC", "ITC.NS", "ITC Limited", "NSE", "FMCG"),
    ("LT", "LT.NS", "Larsen & Toubro", "NSE", "Infrastructure"),
    ("AXISBANK", "AXISBANK.NS", "Axis Bank", "NSE", "Banking"),
    ("SUNPHARMA", "SUNPHARMA.NS", "Sun Pharma", "NSE", "Pharma"),
    ("MARUTI", "MARUTI.NS", "Maruti Suzuki", "NSE", "Auto"),
    ("TATASTEEL", "TATASTEEL.NS", "Tata Steel", "NSE", "Metals"),
    ("BEL", "BEL.NS", "Bharat Electronics", "NSE", "Defence"),
    ("HAL", "HAL.NS", "Hindustan Aeronautics", "NSE", "Defence"),
    ("TRENT", "TRENT.NS", "Trent Limited", "NSE", "Retail"),
]

def main():
    result = {}
    for symbol, yf_symbol, name, exchange, sector in STOCKS:
        print(f"Fetching {symbol}...")
        df = yf.download(yf_symbol, period="60d", progress=False)
        if df.empty:
            print(f"  WARNING: no data for {symbol}, skipping")
            continue
        df = df.dropna()  # drop today's incomplete row if market still open
        df = df.tail(40)
        rows = []
        for idx, row in df.iterrows():
            def val(col):
                v = row[col]
                return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
            rows.append({
                "date": idx.strftime("%Y-%m-%d"),
                "open": val("Open"),
                "high": val("High"),
                "low": val("Low"),
                "close": val("Close"),
                "volume": int(val("Volume")),
            })
        result[symbol] = {
            "company_name": name,
            "exchange": exchange,
            "sector": sector,
            "history": rows,
        }

    out_path = Path(__file__).parent.parent / "backend" / "fixtures" / "market_history.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"\nSaved {len(result)} stocks to {out_path}")

if __name__ == "__main__":
    main()

import sys
import subprocess
import os

def auto_install(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        __import__(import_name)
    except ImportError:
        print(f"[*] Missing package detected: {package}. Auto-installing, please wait...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"[+] {package} successfully installed!")

# Auto-install required packages
auto_install('ccxt')
auto_install('pandas')
auto_install('pandas-ta', 'pandas_ta')
auto_install('colorama')

import ccxt
import pandas as pd
import pandas_ta as ta  # type: ignore
import time
from colorama import init, Fore, Style
import winsound
from datetime import datetime, timedelta

# Initialize colorama for Windows terminal
init(autoreset=True)

# ----------------- CONFIGURATION -----------------
EXCHANGE = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # Binance USDT-M Futures
    }
})
# API Engellerini aşmak için alternatif sunucu (api.binance.com yerine api3.binance.com)
if isinstance(EXCHANGE.urls.get('api'), dict):
    if 'public' in EXCHANGE.urls['api']:
        EXCHANGE.urls['api']['public'] = 'https://api3.binance.com/api/v3'
    if 'sapi' in EXCHANGE.urls['api']:
        EXCHANGE.urls['api']['sapi'] = 'https://api3.binance.com/sapi/v1'

TIMEFRAME = '1h'
LIMIT = 250       # At least 200 candles needed for EMA 200
TOP_COIN_LIMIT = 1000  # Scan all active USDT pairs
SCAN_INTERVAL_MINS = 5 
LOG_FILE = "signals.log"
# -------------------------------------------

GLOBAL_FUNDING_RATES = {}
SIGNAL_HISTORY = {} # To prevent duplicate alerts for the same candle

def log_signal(message):
    """Writes the signal to a log file with a timestamp."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(f"[{timestamp}] {message}\n")

def fetch_all_funding_rates():
    global GLOBAL_FUNDING_RATES
    try:
        sys.stdout.write("\rFetching Funding Rates...                         ")
        sys.stdout.flush()
        rates = EXCHANGE.fetch_funding_rates()
        for sym, data in rates.items():
            if data.get('fundingRate') is not None:
                GLOBAL_FUNDING_RATES[sym] = data['fundingRate']
    except Exception as e:
        print(Fore.RED + f"\n[!] Failed to fetch funding rates: {e}")

def beep_alarm():
    """Plays an alert sound from the computer"""
    try:
        winsound.Beep(1000, 400)
        winsound.Beep(1200, 400)
    except Exception:
        pass

def fetch_data(symbol):
    """Fetches OHLCV data from the exchange."""
    try:
        ohlcv = EXCHANGE.fetch_ohlcv(symbol, TIMEFRAME, limit=LIMIT)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        return None

def analyze_symbol(symbol):
    """Applies the LONG-Only strategy rules."""
    df = fetch_data(symbol)
    if df is None or len(df) < 200:
        return False
    
    # Calculate Indicators
    df.ta.ema(length=200, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.bbands(length=20, std=2, append=True)
    df.ta.macd(fast=12, slow=26, signal=9, append=True)
    df['VOL_SMA_20'] = ta.sma(df['volume'], length=20)
    
    df.dropna(inplace=True)
    if len(df) < 2: return False

    last = df.iloc[-1]
    prev = df.iloc[-2]
    
    # Prevent duplicate signals on the same candle
    current_candle_time = last['timestamp']
    if symbol in SIGNAL_HISTORY and SIGNAL_HISTORY[symbol] == current_candle_time:
        return False

    close = last['close']
    ema_200 = last['EMA_200']
    rsi = last['RSI_14']
    low_bb = last['BBL_20_2.0']
    macd_line = last['MACD_12_26_9']
    macd_signal = last['MACDs_12_26_9']
    prev_macd_line = prev['MACD_12_26_9']
    prev_macd_signal = prev['MACDs_12_26_9']
    volume = last['volume']
    vol_sma = last['VOL_SMA_20']
    
    # ================= STRATEGY RULES =================
    # 1. Trend Filter
    if close < ema_200: return False
        
    # 2. Pullback Opportunity
    is_pullback = (rsi < 40) or (close <= low_bb * 1.005)
    if not is_pullback: return False
        
    # 3. Confirmation
    macd_crossover = (macd_line > macd_signal) and (prev_macd_line <= prev_macd_signal)
    high_volume = volume > vol_sma
    
    # 4. Funding Rate Filter
    funding_rate = GLOBAL_FUNDING_RATES.get(symbol, 0.0)
    is_funding_good = funding_rate <= 0.0001
    
    if macd_crossover and high_volume and is_funding_good:
        # Track signal to prevent double alerts
        SIGNAL_HISTORY[symbol] = current_candle_time
        
        msg = f"LONG SIGNAL: {symbol} | Price: {close:.4f} | RSI: {rsi:.2f} | Funding: {funding_rate*100:.4f}%"
        log_signal(msg)
        
        print(Fore.GREEN + Style.BRIGHT + f"\n[🟩 LONG SIGNAL] {symbol} - {datetime.now().strftime('%H:%M:%S')}")
        print(Fore.WHITE + f" ➜ Price: {close:.4f} (Above EMA 200: {ema_200:.4f})")
        print(Fore.WHITE + f" ➜ RSI: {rsi:.2f} | MACD: Bullish Cross | Volume: Confirmed")
        print(Fore.WHITE + f" ➜ Funding Rate: {funding_rate * 100:.4f}% ({'Healthy' if funding_rate < 0 else 'Normal'})")
        print(Fore.GREEN + "-" * 50)
        return True
        
    return False

def get_top_symbols(limit=50):
    """Fetches the top USDT pairs by volume."""
    try:
        tickers = EXCHANGE.fetch_tickers()
        usdt_pairs = []
        for symbol, ticker in tickers.items():
            if ('/USDT' in symbol) and ticker.get('quoteVolume') is not None:
                if not any(x in symbol for x in ['UP', 'DOWN', 'BEAR', 'BULL', '_']):
                    usdt_pairs.append({'symbol': symbol, 'volume': ticker['quoteVolume']})
        
        usdt_pairs = sorted(usdt_pairs, key=lambda x: x['volume'], reverse=True)
        return [pair['symbol'] for pair in usdt_pairs[:limit]]
    except Exception as e:
        print(Fore.RED + f"\n[!] Failed to fetch market data: {e}")
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.CYAN + Style.BRIGHT + "="*55)
    print(Fore.CYAN + Style.BRIGHT + f"🚀 Hydraulic v2.1 - Professional LONG-Only Scanner")
    print(Fore.CYAN + f"   - Timeframe: {TIMEFRAME} | Target: All active USDT Pairs")
    print(Fore.CYAN + f"   - Interval: Every {SCAN_INTERVAL_MINS} Minutes")
    print(Fore.CYAN + f"   - Logging: Active ({LOG_FILE})")
    print(Fore.CYAN + Style.BRIGHT + "="*55 + "\n")
    
    print(Fore.YELLOW + "Discovering market liquidity...")
    SYMBOLS = get_top_symbols(TOP_COIN_LIMIT)
    print(Fore.GREEN + f"Found {len(SYMBOLS)} target pairs. Starting scan loop...\n")
    
    while True:
        start_time = datetime.now()
        print(Fore.BLUE + f"[{start_time.strftime('%H:%M:%S')}] Scan cycle started...")
        
        fetch_all_funding_rates()
        
        signal_found = False
        for symbol in SYMBOLS:
            sys.stdout.write(f"\rAnalyzing: {symbol:<15}")
            sys.stdout.flush()
            
            if analyze_symbol(symbol):
                signal_found = True
        
        sys.stdout.write("\r" + " "*40 + "\r")
        
        if signal_found:
            beep_alarm()
        else:
            print(Fore.LIGHTBLACK_EX + "   ➥ Scan complete. No new signals found in this cycle.")
            
        print(Fore.LIGHTBLACK_EX + "-" * 55)
        
        # Calculate remaining wait time to keep exact 5-min intervals
        elapsed = (datetime.now() - start_time).total_seconds()
        wait_time = max(10, (SCAN_INTERVAL_MINS * 60) - elapsed)
        
        next_run = datetime.now() + timedelta(seconds=wait_time)
        print(Fore.LIGHTBLACK_EX + f"Next scan scheduled for: {next_run.strftime('%H:%M:%S')}")
        time.sleep(wait_time)

if __name__ == "__main__":
    main()

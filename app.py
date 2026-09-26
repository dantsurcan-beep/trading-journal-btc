import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime
import os

st.set_page_config(page_title="Kraken Universal Trading Journal", layout="wide")

st.title("📊 Jurnal Universal de Trading (Kraken)")
st.write("Monitorizare live și istoric preluat automat direct din bursa Kraken.")

with st.sidebar:
    st.header("🔑 Conexiune Kraken")
    piata_ales = st.selectbox("Alege Piața", ["Futures", "Spot"])
    
    default_key = ""
    default_secret = ""
    
    try:
        if piata_ales == "Futures":
            default_key = st.secrets.get("KRAKEN_FUTURES_KEY", "")
            default_secret = st.secrets.get("KRAKEN_FUTURES_SECRET", "")
        else:
            default_key = st.secrets.get("KRAKEN_SPOT_KEY", "")
            default_secret = st.secrets.get("KRAKEN_SPOT_SECRET", "")
    except Exception:
        pass

    st.markdown("---")
    api_key_input = st.text_input(f"Kraken {piata_ales} API Key", value=default_key, type="password")
    api_secret_input = st.text_input(f"Kraken {piata_ales} API Secret", value=default_secret, type="password")

exchange = None
if api_key_input and api_secret_input:
    try:
        if piata_ales == "Futures":
            exchange = ccxt.krakenfutures({
                'apiKey': api_key_input.strip(),
                'secret': api_secret_input.strip(),
                'enableRateLimit': True
            })
        else:
            exchange = ccxt.kraken({
                'apiKey': api_key_input.strip(),
                'secret': api_secret_input.strip(),
                'enableRateLimit': True
            })
        
        exchange.load_markets()
        st.sidebar.success(f"Conectat la Kraken {piata_ales} cu succes! ✅")
    except Exception as e:
        st.sidebar.error(f"Eroare de conexiune: {e}")

def fetch_active_positions(exc, piata):
    try:
        if piata == "Futures":
            positions = exc.fetch_positions()
            active_pos = [p for p in positions if float(p.get('contracts', 0)) > 0]
            data = []
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            for p in active_pos:
                simbol_curat = p.get('symbol', '').replace(':USD', '').replace('/USD', '')
                pret_intrare = float(p.get('entryPrice', 0) or 0)
                cantitate = float(p.get('contracts', 0) or 0)
                valoare_usd = pret_intrare * cantitate
                pnl = float(p.get('unrealizedPnl', 0) or 0)
                
                data.append({
                    "Data Preluării": now_str,
                    "Simbol": simbol_curat,
                    "Direcție": p.get('side', 'N/A').upper(),
                    "Preț Intrare (\()": f"\){pret_intrare:,.2f}",
                    "Cantitate": cantitate,
                    "Valoare Notională (\()": f"\){valoare_usd:,.2f}",
                    "P&L Nerealizat (\()": f"\){pnl:+,.2f}",
                    "Preț Lichidare": p.get('liquidationPrice', 'N/A')
                })
            return pd.DataFrame(data)
        else:
            balance = exc.fetch_balance()
            free_bal = balance.get('free', {})
            data = []
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            for asset, amount in free_bal.items():
                if amount > 0 and asset not in ['ZUSD', 'ZEUR', 'USDT', 'USDC']:
                    data.append({
                        "Data Preluării": now_str,
                        "Monedă": asset,
                        "Cantitate Disponibilă": amount
                    })
            return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Nu s-au putut prelua pozițiile active: {e}")
        return pd.DataFrame()

def fetch_closed_trades_history(exc, piata):
    try:
        data = []
        if piata == "Futures":
            # Preluăm ordinele închise / executate din istoricul Kraken Futures
            orders = exc.fetch_closed_orders()
            for o in orders:
                if o.get('status') == 'closed':
                    timestamp = o.get('timestamp')
                    data_ora = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M') if timestamp else 'N/A'
                    simbol_curat = o.get('symbol', '').replace(':USD', '').replace('/USD', '')
                    
                    data.append({
                        "Data & Ora": data_ora,
                        "Piață": piata,
                        "Simbol": simbol_curat,
                        "Tip": o.get('side', 'N/A').upper(),
                        "Preț Execuție (\()": f"\){float(o.get('price', 0) or 0):,.2f}",
                        "Cantitate": o.get('amount', 0),
                        "Cost / Valoare (\()": f"\){float(o.get('cost', 0) or 0):,.2f}",
                        "Status": o.get('status', 'N/A')
                    })
        else:
            # Pentru Spot, preluăm tranzacțiile istorice executate
            trades = exc.fetch_my_trades()
            for t in trades:
                timestamp = t.get('timestamp')
                data_ora = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M') if timestamp else 'N/A'
                
                data.append({
                    "Data & Ora": data_ora,
                    "Piață": piata,
                    "Simbol": t.get('symbol', 'N/A'),
                    "Tip": t.get('side', 'N/A').upper(),
                    "Preț Execuție (\()": f"\){float(t.get('price', 0) or 0):,.2f}",
                    "Cantitate": t.get('amount', 0),
                    "Cost / Valoare (\()": f"\){float(t.get('cost', 0) or 0):,.2f}",
                    "Comision (\()": f"\){float(t.get('fee', {}).get('cost', 0) or 0):,.2f}"
                })
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Nu s-a putut prelua istoricul automat: {e}")
        return pd.DataFrame()

if exchange:
    tab1, tab2 = st.tabs(["📌 Poziții Active Live", "📜 Istoricul Universal (Preluat Automat)"])
    
    with tab1:
        st.subheader(f"Monitorizare în timp real - Kraken {piata_ales}")
        df_active = fetch_active_positions(exchange, piata_ales)
        if not df_active.empty:
            st.dataframe(df_active, use_container_width=True, hide_index=True)
        else:
            st.info("Momentan nu ai poziții active sau active în portofoliu.")
            
    with tab2:
        st.subheader(f"Istoricul Automat - Kraken {piata_ales}")
        st.info("Această listă este populată în mod automat direct cu tranzacțiile tale încheiate preluate din bursa Kraken.")
        
        df_istoric = fetch_closed_trades_history(exchange, piata_ales)
        if not df_istoric.empty:
            st.dataframe(df_istoric, use_container_width=True, hide_index=True)
            
            csv_export = df_istoric.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descarcă istoricul complet (CSV)",
                data=csv_export,
                file_name="istoric_kraken_automat.csv",
                mime="text/csv",
            )
        else:
            st.info("Nu s-au găsit tranzacții închise în istoricul contului sau permisiunile API necesită verificare.")
else:
    st.info("👈 Introdu cheile API în meniul din stânga pentru a începe.")

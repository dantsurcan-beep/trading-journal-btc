import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime
import os

st.set_page_config(page_title="BTC Perpetual Trading Journal", layout="wide")

st.title("₿ Jurnal Bitcoin Perpetual (Kraken Futures)")
st.write("Monitorizează exclusiv pozițiile tale de BTC, istoricul complet și comisioanele.")

DB_FILE = "btc_trading_journal.csv"

def load_persistent_history():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        return pd.DataFrame(columns=[
            "Data", "Simbol", "Tip (Long/Short)", "Preț Intrare", 
            "Cantitate (Contracte)", "Status", "Preț Ieșire", 
            "Comision Kraken", "Profit/Pierdere Net (PnL)"
        ])

api_key_input = ""
api_secret_input = ""

try:
    api_key_input = st.secrets.get("KRAKEN_API_KEY", "")
    api_secret_input = st.secrets.get("KRAKEN_API_SECRET", "")
except Exception:
    pass

with st.sidebar:
    st.header("🔑 Conexiune Kraken Futures")
    if not api_key_input:
        api_key_input = st.text_input("Kraken API Key", type="password")
    else:
        st.success("API Key încărcat automat! 🔒")
        
    if not api_secret_input:
        api_secret_input = st.text_input("Kraken API Secret", type="password")
    else:
        st.success("API Secret încărcat automat! 🔒")

exchange = None
if api_key_input and api_secret_input:
    try:
        exchange = ccxt.krakenfutures({
            'apiKey': api_key_input.strip(),
            'secret': api_secret_input.strip(),
            'enableRateLimit': True
        })
        exchange.load_markets()
        st.sidebar.success("Conectat la Kraken cu succes!")
    except Exception as e:
        st.error(f"Eroare de conexiune API: {e}")

def fetch_btc_positions(exc):
    try:
        positions = exc.fetch_positions()
        btc_positions = [
            p for p in positions 
            if float(p.get('contracts', 0)) > 0 and ('BTC' in p.get('symbol', '').upper() or 'XBT' in p.get('symbol', '').upper())
        ]
        data = []
        for p in btc_positions:
            data.append({
                "Simbol": p.get('symbol'),
                "Direcție": p.get('side', 'N/A').upper(),
                "Preț Intrare": p.get('entryPrice'),
                "Contracte": p.get('contracts'),
                "Valoare Notională": p.get('notional'),
                "P&L Nerealizat": p.get('unrealizedPnl'),
                "Preț Lichidare": p.get('liquidationPrice')
            })
        return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Nu s-au putut prelua pozițiile active: {e}")
        return pd.DataFrame()

if exchange:
    tab1, tab2, tab3 = st.tabs(["📌 Poziție BTC Activă (Live)", "➕ Adaugă Manual în Istoric", "📜 Istoricul Permanent (Salvat)"])
    
    with tab1:
        st.subheader("Poziția ta curentă pe Bitcoin Perpetual")
        st.info("Chiar dacă ai avut laptopul închis, aici vezi situația actuală direct din bursa Kraken.")
        df_active = fetch_btc_positions(exchange)
        if not df_active.empty:
            st.dataframe(df_active, use_container_width=True)
        else:
            st.warning("Momentan nu ai nicio poziție deschisă pe Bitcoin pe Kraken Futures.")
            
    with tab2:
        st.subheader("Jurnal Manual / Arhivare Tranzacții Închise")
        st.markdown("Folosește acest formular pentru a salva definitiv o tranzacție încheiată. Istoricul salvat aici **nu se va șterge niciodată**.")
        
        with st.form("manual_trade_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                simbol_btc = st.text_input("Simbol", value="PI_XBTUSD")
                tip_tranzactie = st.selectbox("Direcție", ["Long", "Short"])
                pret_intrare = st.number_input("Preț de Intrare ($)", min_value=0.0, format="%.2f")
                cantitate = st.number_input("Cantitate / Contracte", min_value=0.0, format="%.4f")
            with c2:
                status_iesire = st.selectbox("Cum s-a încheiat?", ["Take Profit", "Stop Loss", "Închis Manual"])
                pret_iesire = st.number_input("Preț de Iesire ($)", min_value=0.0, format="%.2f")
                comision_kraken = st.number_input("Comision Kraken ($)", min_value=0.0, format="%.2f")
                
            buton_salvare = st.form_submit_button("Salvează în Istoricul Permanent")
            
            if buton_salvare:
                if tip_tranzactie == "Long":
                    pnl_brut = (pret_iesire - pret_intrare) * cantitate
                else:
                    pnl_brut = (pret_intrare - pret_iesire) * cantitate
                pnl_net = pnl_brut - comision_kraken
                
                data_ora = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                rand_nou = pd.DataFrame([{
                    "Data": data_ora,
                    "Simbol": simbol_btc,
                    "Tip (Long/Short)": tip_tranzactie,
                    "Preț Intrare": pret_intrare,
                    "Cantitate (Contracte)": cantitate,
                    "Status": status_iesire,
                    "Preț Ieșire": pret_iesire,
                    "Comision Kraken": comision_kraken,
                    "Profit/Pierdere Net (PnL)": pnl_net
                }])
                
                df_hist = load_persistent_history()
                df_hist = pd.concat([df_hist, rand_nou], ignore_index=True)
                df_hist.to_csv(DB_FILE, index=False)
                st.success("Tranzacția a fost salvată permanent în istoricul tău!")

    with tab3:
        st.subheader("Arhiva ta permanentă de tranzacții Bitcoin")
        df_istoric = load_persistent_history()
        
        if not df_istoric.empty:
            total_comisioane = df_istoric["Comision Kraken"].sum()
            total_pnl = df_istoric["Profit/Pierdere Net (PnL)"].sum()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total Comisioane Plătite", f"${total_comisioane:.2f}")
            col_m2.metric("Profit / Pierdere Net Total", f"${total_pnl:.2f}")
            col_m3.metric("Total Tranzacții Înregistrate", len(df_istoric))
            
            st.dataframe(df_istoric, use_container_width=True)
            
            csv_export = df_istoric.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Descarcă o copie de rezervă a istoricului (CSV)",
                data=csv_export,
                file_name="backup_istoric_btc.csv",
                mime="text/csv",
            )
        else:
            st.info("Istoricul este gol momentan. Adaugă tranzacții din tab-ul anterior.")
else:
    st.info("👈 Introdu cheile API în stânga sau asigură-te că fișierul secrets.toml este completat corect.")

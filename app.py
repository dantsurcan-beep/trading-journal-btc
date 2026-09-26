import streamlit as st
import pandas as pd
import ccxt
from datetime import datetime
import os

st.set_page_config(page_title="Kraken Universal Trading Journal", layout="wide")

st.title("📊 Jurnal Universal de Trading (Kraken)")
st.write("Jurnalul tău centralizat pentru orice monedă (Spot sau Futures), cu date complete, valori în USD și PnL.")

DB_FILE = "universal_trading_journal.csv"

def load_persistent_history():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    else:
        return pd.DataFrame(columns=[
            "Data", "Piață", "Simbol / Monedă", "Tip (Long/Short)", "Preț Intrare", 
            "Cantitate", "Valoare USD", "Status", "Preț Ieșire", 
            "Comision Kraken", "Profit/Pierdere Net (PnL)"
        ])

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

def fetch_all_positions(exc, piata):
    try:
        if piata == "Futures":
            positions = exc.fetch_positions()
            active_pos = [p for p in positions if float(p.get('contracts', 0)) > 0]
            data = []
            for p in active_pos:
                data.append({
                    "Simbol": p.get('symbol'),
                    "Direcție": p.get('side', 'N/A').upper(),
                    "Preț Intrare": p.get('entryPrice'),
                    "Cantitate": p.get('contracts'),
                    "Valoare Notională ($)": p.get('notional'),
                    "P&L Nerealizat ($)": p.get('unrealizedPnl'),
                    "Preț Lichidare": p.get('liquidationPrice')
                })
            return pd.DataFrame(data)
        else:
            balance = exc.fetch_balance()
            free_bal = balance.get('free', {})
            data = []
            for asset, amount in free_bal.items():
                if amount > 0 and asset not in ['ZUSD', 'ZEUR', 'USDT', 'USDC']:
                    data.append({
                        "Monedă": asset,
                        "Cantitate Disponibilă": amount
                    })
            return pd.DataFrame(data)
    except Exception as e:
        st.warning(f"Nu s-au putut prelua datele live: {e}")
        return pd.DataFrame()

if exchange:
    tab1, tab2, tab3 = st.tabs(["📌 Poziții / Active Live", "➕ Adaugă Tranzacție în Jurnal", "📜 Istoricul Universal (Salvat)"])
    
    with tab1:
        st.subheader(f"Monitorizare în timp real - Kraken {piata_ales}")
        st.info("Aici vezi toate activele sau pozițiile tale deschise pe orice monedă, direct din bursa Kraken.")
        df_active = fetch_all_positions(exchange, piata_ales)
        if not df_active.empty:
            st.dataframe(df_active, use_container_width=True)
        else:
            st.info("Momentan nu ai poziții active sau active în portofoliu.")
            
    with tab2:
        st.subheader("Jurnal Universal de Tranzacții")
        st.markdown("Completează detaliile tranzacției. Jurnalul va înregistra data, moneda, valoarea în USD și rezultatul final.")
        
        with st.form("universal_trade_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                moneda_simbol = st.text_input("Simbol / Monedă (ex: SOL/USD, BTC/USD, ETH)", value="BTC/USD")
                tip_tranzactie = st.selectbox("Direcție", ["Long", "Short"])
                pret_intrare = st.number_input("Preț de Intrare ($)", min_value=0.0, format="%.2f")
                cantitate = st.number_input("Cantitate Tranzacționată", min_value=0.0, format="%.4f")
            with c2:
                status_iesire = st.selectbox("Status Ieșire", ["Take Profit", "Stop Loss", "Închis Manual"])
                pret_iesire = st.number_input("Preț de Iesire ($)", min_value=0.0, format="%.2f")
                comision_kraken = st.number_input("Comision Kraken ($)", min_value=0.0, format="%.2f")
                
            buton_salvare = st.form_submit_button("Salvează Tranzacția în Jurnal")
            
            if buton_salvare:
                valoare_usd = pret_intrare * cantitate
                
                if tip_tranzactie == "Long":
                    pnl_brut = (pret_iesire - pret_intrare) * cantitate
                else:
                    pnl_brut = (pret_intrare - pret_iesire) * cantitate
                pnl_net = pnl_brut - comision_kraken
                
                data_ora = datetime.now().strftime("%Y-%m-%d %H:%M")
                
                rand_nou = pd.DataFrame([{
                    "Data": data_ora,
                    "Piață": piata_ales,
                    "Simbol / Monedă": moneda_simbol.upper(),
                    "Tip (Long/Short)": tip_tranzactie,
                    "Preț Intrare": pret_intrare,
                    "Cantitate": cantitate,
                    "Valoare USD": valoare_usd,
                    "Status": status_iesire,
                    "Preț Ieșire": pret_iesire,
                    "Comision Kraken": comision_kraken,
                    "Profit/Pierdere Net (PnL)": pnl_net
                }])
                
                df_hist = load_persistent_history()
                df_hist = pd.concat([df_hist, rand_nou], ignore_index=True)
                df_hist.to_csv(DB_FILE, index=False)
                st.success("Tranzacția a fost înregistrată cu succes în jurnal!")

    with tab3:
        st.subheader("Arhiva Universală de Tranzacții")
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
                label="📥 Descarcă arhiva completă (CSV)",
                data=csv_export,
                file_name="jurnal_universal_trading.csv",
                mime="text/csv",
            )
        else:
            st.info("Jurnalul este gol momentan. Adaugă prima tranzacție din tab-ul anterior.")
else:
    st.info("👈 Introdu cheile API în meniul din stânga pentru a începe.")

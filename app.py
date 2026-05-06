import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from streamlit_autorefresh import st_autorefresh
from collections import Counter
import json  # Secrets dosyasını okumak için gerekli

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="La Familia", page_icon="🔥", layout="centered")

# --- MODERN UYGULAMA TASARIMI (CSS INJECTION) ---
st.markdown("""
    <style>
        .stApp {
            background-color: #0E1117;
            color: #E2E8F0;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        div.stButton > button {
            background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%);
            color: white;
            border: none;
            border-radius: 12px;
            padding: 10px 24px;
            font-weight: 700;
            letter-spacing: 0.5px;
            transition: all 0.3s ease-in-out;
            width: 100%;
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0px 8px 15px rgba(255, 75, 43, 0.4);
        }
        
        .stTextInput > div > div > input {
            border-radius: 10px;
            border: 1px solid #334155;
            background-color: #1E293B;
            color: white;
            padding: 12px;
        }
    </style>
""", unsafe_allow_html=True)

st_autorefresh(interval=3000, key="data_refresh")

# --- FİREBASE BAĞLANTISI (AKILLI SİSTEM) ---
if not firebase_admin._apps:
    # 1. Senaryo: Streamlit Cloud (Secrets) üzerinden bağlanma
    if "firebase" in st.secrets:
        # Dashboard'a yapıştırdığın metni JSON'a çeviriyoruz
        key_dict = json.loads(st.secrets["firebase"]["textkey"])
        cred = credentials.Certificate(key_dict)
    # 2. Senaryo: Kendi bilgisayarında (Dosyadan) çalışma
    else:
        cred = credentials.Certificate("firebase_key.json")
    
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- VERİ TABANI KONTROLLERİ ---
oyun_ref = db.collection("oyun_odasi").document("merkez")
oyun_verisi = oyun_ref.get().to_dict()

if not oyun_verisi:
    oyun_ref.set({"asama": "lobi", "oyuncular": [], "sorular": [], "oylar_listesi": []})
    oyun_verisi = {"asama": "lobi", "oyuncular": [], "sorular": [], "oylar_listesi": []}

asama = oyun_verisi.get("asama", "lobi")
oyuncular = oyun_verisi.get("oyuncular", [])
sorular = oyun_verisi.get("sorular", [])
oylar_listesi = oyun_verisi.get("oylar_listesi", [])

if "benim_adim" not in st.session_state:
    st.session_state.benim_adim = ""
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# --- ANA BAŞLIK ---
st.markdown("<h1 style='text-align: center; color: #FF4B2B;'>🔥 La Familia Konseyi</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94A3B8;'>Hoşgeldiniz. Lütfen kemerlerinizi bağlayın.</p>", unsafe_allow_html=True)

# ==========================================
# GİZLİ YÖNETİCİ PANELİ (Açılır Kutu)
# ==========================================
with st.expander("⚙️ Kurucu Paneli (Sadece Yönetici)"):
    if not st.session_state.is_admin:
        admin_pass = st.text_input("Şifre:", type="password")
        if st.button("Yetki Al"):
            if admin_pass == "cansın": # Şifren burada kalsın
                st.session_state.is_admin = True
                st.success("Yetki onaylandı! 👑 Butonlar açıldı.")
                st.rerun()
            else:
                st.error("Yanlış şifre!")
    else:
        st.success("Admin yetkisi aktif. 👑")
        if st.button("Yetkiyi Bırak"):
            st.session_state.is_admin = False
            st.rerun()

st.divider()

# --- OYUN AKIŞI (Lobi, Soru Yazma, Oylama) ---
if asama == "lobi":
    st.markdown("### 🛋️ Lobi: Bekleme Salonu")
    ad = st.text_input("Konseye hangi isimle katılıyorsun?", value=st.session_state.benim_adim)
    if st.button("Odaya Katıl"):
        if ad and ad not in oyuncular:
            oyun_ref.update({"oyuncular": firestore.ArrayUnion([ad])})
            st.session_state.benim_adim = ad
            st.success("Katıldın! Diğerlerini bekle...")
        elif ad in oyuncular:
            st.session_state.benim_adim = ad
            st.success("Zaten odadasın.")
    st.info(f"Odadakiler: {', '.join(oyuncular) if oyuncular else 'Kimse yok'}")
    if st.session_state.is_admin:
        if st.button("Oyunu Başlat"):
            if len(oyuncular) >= 2:
                oyun_ref.update({"asama": "soru_yazma"})

elif asama == "soru_yazma":
    st.markdown("### 🕵️ Anonim Soru Vakti")
    yeni_soru = st.text_input("Kışkırtıcı sorunu yaz:")
    if st.button("Soruyu Gizlice Havuza At"):
        if yeni_soru:
            oyun_ref.update({"sorular": firestore.ArrayUnion([yeni_soru])})
            st.success("Soru havuzda!")
    st.info(f"Havuzdaki soru sayısı: **{len(sorular)}**")
    if st.session_state.is_admin:
        if st.button("👑 Oylamaya Geç"):
            oyun_ref.update({"asama": "oylama"})

elif asama == "oylama":
    st.markdown("### 🗳️ Yüzleşme Arenası")
    for i, soru in enumerate(sorular):
        with st.expander(f"Soru {i+1}: {soru}", expanded=True):
            secim = st.radio("Sence bu kim?", oyuncular, key=f"radio_{i}", horizontal=True)
            if st.button("Oyumu Gönder", key=f"btn_{i}"):
                oyun_ref.update({"oylar_listesi": firestore.ArrayUnion([f"{i}_{secim}"])})
                st.toast("Oy kaydedildi! 🎯")
    if st.session_state.is_admin:
        if st.button("👑 Sonuçları Açıkla"):
            oyun_ref.update({"asama": "sonuclar"})

# ==========================================
# 4. AŞAMA: SONUÇLAR VE KAOS
# ==========================================
elif asama == "sonuclar":
    st.markdown("<h2 style='text-align: center; color: #FF4B2B;'>🏆 Konsey Genel Sonuçları</h2>", unsafe_allow_html=True)
    st.balloons()
    
    tum_oylar_havuzu = [oy.split("_")[1] for oy in oylar_listesi]
    
    if tum_oylar_havuzu:
        genel_sayim = Counter(tum_oylar_havuzu)
        en_yuksek = max(genel_sayim.values())
        kazananlar = [kisi for kisi, oy in genel_sayim.items() if oy == en_yuksek]
        
        st.markdown(f"""
            <div style='background: linear-gradient(135deg, #FF416C 0%, #FF4B2B 100%); padding:25px; border-radius:20px; text-align:center; margin-bottom:30px;'>
                <h2 style='color:white; margin:0;'>👑 GÜNÜN KAOS ŞAMPİYONU</h2>
                <h1 style='color:white; font-size:2.5rem;'>{" & ".join(kazananlar)}</h1>
                <p style='color:white;'>Toplam {en_yuksek} oy!</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📊 Genel Puan Durumu")
        for kisi, toplam_oy in genel_sayim.most_common():
            yuzde = int((toplam_oy / len(tum_oylar_havuzu)) * 100)
            st.markdown(f"""
                <div style='display: flex; justify-content: space-between; background-color:#1E293B; padding:15px; border-radius:10px; margin-bottom:10px;'>
                    <span>{kisi}</span>
                    <span style='color:#FF4B2B; font-weight:bold;'>{toplam_oy} Oy (%{yuzde})</span>
                </div>
            """, unsafe_allow_html=True)
    
    if st.session_state.is_admin:
        if st.button("🔄 Yeni Oyuna Başla"):
            oyun_ref.set({"asama": "lobi", "oyuncular": [], "sorular": [], "oylar_listesi": []})
            st.rerun()
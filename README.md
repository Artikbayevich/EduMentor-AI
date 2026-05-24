<div align="center">
  <img src="https://raw.githubusercontent.com/Artikbayevich/EduMentor-AI/main/frontend/src/assets/react.svg" alt="EduMentor AI" width="100"/>
  <h1>EduMentor AI 🎓🤖</h1>
  <p><b>Talabalar uchun sun'iy intellektga asoslangan P2P ta'lim va gamifikatsiya platformasi.</b></p>
  <p>Bu loyiha "Build with AI Hackathon" uchun tayyorlangan!</p>
</div>

---

## 📌 Loyiha Haqida

**EduMentor AI** — bu universitet talabalari o'rtasida o'zaro tajriba almashish (P2P - Peer-to-Peer) va dars o'zlashtirishini oshirishga qaratilgan platforma. Tizim universitetning baholash tizimi (masalan, HEMIS) bilan integratsiya qilinib, talaba dars qoldirganda sun'iy intellekt orqali o'sha darsning qisqacha mazmuni va testlarini generatsiya qiladi. O'quvchi buni o'qib-o'rganib, testlarni yechish orqali **EduCoin** ishlab topadi.

Ishlab topilgan Coin'larni talaba **Skill Market** bo'limida boshqa iqtidorli talabalarning masterklasslarida qatnashish uchun yoki **Yordam bozori**da kimgadir pul to'lash uchun sarflashi mumkin!

## 🚀 Qilingan Ishlar va Ishlayotgan Funksiyalar (Hackathon Demo)

✅ **1. Avtomatlashtirilgan AI Dars Konspekti va Testlar**
- O'qituvchi qoldirilgan dars (NB) kiritgan zahoti, tizim (Ollama LLM va Langchain yordamida) dars mavzusiga oid qisqacha ma'ruza matni va 2-3 ta interaktiv test yaratadi.
- *(Agar mahalliy kompyuterda AI ishlamasa, avtomatlashtirilgan Mock-Fallback tizimi ishga tushadi).*

✅ **2. Telegram Bot Integratsiyasi**
- Talaba dars qoldirganligi haqida zudlik bilan Telegram bot orqali ogohlantirish oladi va maxsus havolaga o'tib darsni qoplash imkoniyatiga ega bo'ladi.

✅ **3. AI Skill Match (Aql bilan sherik topish)**
- Foydalanuvchi "O'rgata olaman" va "O'rganmoqchiman" fanlarini kiritadi.
- Tizimdagi "SentenceTransformer" algoritmlari orqali talabaga eng mos mentor yoki "study-buddy" tavsiya qilinadi (SWAP, MENTOR, STUDY toifalari orqali).

✅ **4. Skill Market (Masterklasslar)**
- Iqtidorli talabalar o'zlari bilgan fandan "Masterklass" (Mini-kurs) e'lon qilib EduCoin ishlashlari mumkin.
- Boshqalar EduCoin evaziga ushbu darslarni sotib olishi va qatnashuvchilar soni belgilangan limitga yetganda dars boshlanishi mumkin.

✅ **5. Gamifikatsiya va Leaderboard**
- Talabalar test yechish, kimgadir yordam berish orqali coin yig'adilar va Universitet/Milliy reytinglarda yuqoriga ko'tariladilar.

## 🛠 Texnologiyalar (Tech Stack)

### 🖥 Backend & AI
- **Python Framework:** FastAPI
- **Database:** PostgreSQL (asyncpg)
- **ORM & Migrations:** SQLAlchemy 2.0 (async), Alembic
- **Sun'iy Intellekt (AI):** LangChain, ChromaDB, Ollama (Llama 3 / Mistral), SentenceTransformers
- **Bot:** Aiogram 3 (Telegram API)

### 🎨 Frontend
- **Framework:** React.js (Vite)
- **Styling:** Tailwind CSS
- **Data Fetching:** React Query & Axios
- **Routing:** React Router v6

## 🎯 Features (Kelgusi Imkoniyatlar / Hali ishlamayotgan qismlar)

Quyidagi funksiyalar Hackathon loyihasining kelgusi bosqichlarida qo'shilishi rejalashtirilgan (hozirgi demo versiyada bu qismlar "Mock" datalar yordamida ko'rsatilgan yoki hali to'liq ulanmagan):

- 🚧 **Haqiqiy HEMIS API bilan Integratsiya:** Hozircha o'qituvchining dars kiritishi va baholar alohida demo panel (HemisTeacherDemo.jsx) orqali simulyatsiya qilinadi.
- 🚧 **JWT Autentifikatsiya (Login/Register):** Backend qismida to'liq yozilgan bo'lsa-da, Frontend qismida hozircha hakamlar uchun osonroq tekshirish maqsadida ochiq holda qoldirilgan.
- 🚧 **Video Chat va Jonli dars xonalari:** Talabalar bir-biriga tushuntirish berayotganda platformaning o'zida WebRTC yoki Zoom API orqali bog'lanishlari.
- 🚧 **Haqiqiy Real-time Chartlar:** Dashboard'dagi davomat va statistika grafiklarni jonli o'zgaradigan holatga keltirish.

## ⚙️ Mahalliy (Local) Muhitda Ishga Tushirish

### Backend & Bot
```bash
# 1. Virtual muhit (venv) yaratish
python -m venv .venv
.\.venv\Scripts\activate   # Windows uchun

# 2. Kutubxonalarni o'rnatish
pip install -r requirements.txt

# 3. Bazani ulamasdan oldin .env fayl yarating (namuna .env.example da bor)

# 4. FastAPI serverni yoqish
uvicorn main:app --reload --port 8000

# 5. Boshqa terminalda Telegram Botni yoqish
python -m bot.main
```

### Frontend
```bash
# 1. Frontend papkasiga o'tish
cd frontend

# 2. Paketlarni o'rnatish
npm install

# 3. React serverni yoqish
npm run dev
```

Platforma odatda `http://localhost:5173` manzilida ishga tushadi! Backend API hujjatlari esa `http://localhost:8000/api/v1/docs` manzilida joylashgan.

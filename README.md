
# 🧠 AuditPRO‑Edge: منصة تدقيق العقود الذكية بالذكاء الاصطناعي

[![CI](https://github.com/Mowafag100/AuditPRO-Edge/actions/workflows/ci.yml/badge.svg)](https://github.com/Mowafag100/AuditPRO-Edge/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.138+-green)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.2+-purple)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**منصة متكاملة لتحليل العقود القانونية والعقود الذكية باستخدام الذكاء الاصطناعي المحلي (Llama3) مع RAG و LangGraph ومراقبة متقدمة.**

---

## ✨ الميزات الرئيسية

- **🔍 تحليل ذكي**: استخدام نموذج Llama3 المحلي (عبر Ollama) لاستخراج المخاطر والتوصيات من المستندات.
- **🧠 RAG المتقدم**: استرجاع السياق من قاعدة متجهات (ChromaDB) لتحسين دقة التحليل.
- **🤖 LangGraph Agents**: وكيل متعدد الخطوات يسترجع السياق ثم يحلل العقد.
- **📊 مراقبة كاملة**: نقاط `/health` و `/metrics` مع Prometheus لتتبع أداء النظام.
- **📝 تسجيل منظم**: باستخدام `structlog` مع تنسيق JSON لسهولة التحليل.
- **🧪 تقييم الجودة**: نظام لتقييم دقة واستدعاء التحليل مقابل نصوص مرجعية.
- **🐳 تشغيل سهل**: مع Docker Compose، تشغيل كل الخدمات (Ollama, ChromaDB, PostgreSQL, Redis, FastAPI, Next.js) بأمر واحد.
- **⚙️ CI/CD**: GitHub Actions للاختبار والبناء التلقائي.

---

## 🏗️ التقنيات المستخدمة

| المكون | التقنية |
| :--- | :--- |
| **Backend** | FastAPI + Python 3.11 |
| **Frontend** | Next.js 16 (React + Turbopack) |
| **قاعدة البيانات** | PostgreSQL (علائقية) + SQLite (للتطوير) |
| **قاعدة المتجهات** | ChromaDB (RAG) |
| **الذكاء الاصطناعي** | Ollama + Llama3 8B |
| **العوامل الذكية** | LangGraph |
| **المراقبة** | Prometheus (نقاط `/metrics`) |
| **التسجيل** | structlog (JSON logs) |
| **CI/CD** | GitHub Actions |
| **الحاويات** | Docker + Docker Compose |

---

## 🚀 التشغيل السريع (للمطورين)

### المتطلبات المسبقة
- Docker + Docker Compose
- Git
- 8GB+ RAM (موصى به 16GB)

### 1. استنساخ المشروع
```bash
git clone https://github.com/Mowafag100/AuditPRO-Edge.git
cd AuditPRO-Edge
2. تشغيل جميع الخدمات (Docker)
bash
docker compose up -d
3. تحميل نموذج Llama3 (أول مرة فقط)
bash
docker compose exec ollama ollama pull llama3
4. فتح الواجهة الأمامية
http://localhost:3000

5. اختبار نقاط API
bash
# تسجيل الدخول للحصول على توكن
TOKEN=$(curl -s -X POST http://localhost:8090/login | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# تحليل ملف PDF
curl -X POST http://localhost:8090/analyze-contract \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_contract.pdf"
📷 لقطات الشاشة
<img width="956" height="535" alt="لقطة شاشة 2026-06-25 015143" src="https://github.com/user-attachments/assets/31bb3299-ba5f-40d4-bec3-02587cb59ffb" />
<img width="958" height="536" alt="لقطة شاشة 2026-06-25 015128" src="https://github.com/user-attachments/assets/80554f3e-04e6-401a-b0ae-84f696b1f5bc" />


يُرجى إضافة صور توضيحية هنا (سأرفقها لاحقاً).

📂 هيكل المشروع
text
AuditPRO-Edge/
├── agents/
│   └── audit_graph.py          # وكيل LangGraph
├── src/
│   ├── logging_config.py       # إعدادات structlog
│   └── evaluation.py           # نظام التقييم
├── tests/
│   └── test_api.py             # اختبارات CI
├── .github/workflows/
│   └── ci.yml                  # GitHub Actions
├── main.py                     # نقطة الدخول الرئيسية لـ FastAPI
├── docker-compose.yml          # تشغيل جميع الخدمات
├── requirements.txt            # تبعيات Python
├── .env.example                # مثال لمتغيرات البيئة
└── README.md                   # هذا الملف
🧪 الاختبار والتقييم
اختبار وحدات: pytest tests/

تقييم التحليل: استخدم نقطة /evaluate مع نص مرجعي.

مراقبة الأداء: http://localhost:8090/metrics (متوافق مع Prometheus).

🤝 المساهمة
نرحب بمساهماتكم! يُرجى اتباع الخطوات:

Fork المشروع.

أنشئ فرعاً جديداً (git checkout -b feature/amazing-feature).

أضف تغييراتك واختباراتها.

ادفع إلى الفرع (git push origin feature/amazing-feature).

افتح طلب سحب (Pull Request).

📜 الترخيص
هذا المشروع مرخص تحت MIT License.

📧 التواصل
المطور: Mowafag Fawzy

البريد الإلكتروني: mowafagfawzy@gmail.com

GitHub: Mowafag100

🌟 إذا أعجبك المشروع، لا تنسَ منحه نجمة (Star) على GitHub!

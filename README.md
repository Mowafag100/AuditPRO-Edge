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

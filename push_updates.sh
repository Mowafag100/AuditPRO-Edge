#!/bin/bash
echo "🚀 Starting Auto-Update & Push..."

# 1. تنظيف الملفات المؤقتة
rm -rf __pycache__
rm -rf .next
echo "🧹 Cleanup complete."

# 2. تحديث المستودع
git add .
git commit -m "Update v2: Typewriter effect, optimized prompt, and UI metrics"

# 3. الرفع (سيستخدم التوكن المخزن)
git push origin main

echo "✅ Push successful! Visit: https://github.com/Mowafag100/AuditPRO-Edge"

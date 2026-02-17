#!/bin/bash

cd ~/bot_university || exit 1

# التحقق من وجود تغييرات
if ! git diff-index --quiet HEAD --; then
    # إضافة كل التغييرات
    git add .

    # عمل commit برسالة زمنية
    git commit -m "Auto commit: $(date '+%Y-%m-%d %H:%M:%S')"

    # رفع التغييرات للريبو
    git push origin master
else
    echo "لا توجد تغييرات جديدة لرفعها"
fi

import urllib.parse

def extract_pdf_info(url):
    try:
        # 🌟 فك تشفير الرابط عشان نجيب اسم الملف الأصلي (لو فيه رموز زي %20)
        parsed_url = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed_url.path)
        
        # استخراج اسم الملف
        filename = path.split("/")[-1]
        
        if not filename or '.' not in filename:
            filename = "document.pdf"

        # 🌟 قائمة بالامتدادات المدعومة
        supported_extensions = (
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', 
            '.txt', '.csv', '.zip', '.rar', '.7z', '.tar', '.gz',
            '.apk', '.epub', '.json', '.xml', '.html', '.rtf'
        )

        # التأكد من أن الملف ينتهي بامتداد مدعوم
        if not filename.lower().endswith(supported_extensions):
            ext = filename.split('.')[-1] if '.' in filename else 'pdf'
            filename = f"document.{ext}"

        # استخراج الامتداد النهائي بدون النقطة
        file_type = filename.split(".")[-1].lower()

        # تنظيف اسم الملف من أي رموز غريبة
        title = filename.replace("_", " ").replace("-", " ").title()

        return {
            "title": title,          # الاسم اللي هيظهر للمستخدم
            "file_url": url,         # رابط التحميل
            "download_url": url,     # 🌟 مهم جداً عشان التطبيق يلاقي الرابط
            "file_type": file_type,  # الامتداد (pdf, xlsx, zip...)
            "size": None             # الحجم هيتم معرفته أثناء التحميل
        }
        
    except Exception as e:
        print(f"Document extraction error: {e}")
        return {
            "title": "Document",
            "file_url": url,
            "download_url": url,
            "file_type": "unknown"
        }

def extract_pdf_info(url):
    # التأكد البسيط من الرابط أو جلب تفاصيل الملف المباشر
    filename = url.split("/")[-1].split("?")[0]
    if not filename.endswith(('.pdf', '.doc', '.docx', '.zip', '.txt')):
        filename = "document.pdf"

    return {
        "title": filename,
        "file_url": url,
        "file_type": filename.split(".")[-1]
    }
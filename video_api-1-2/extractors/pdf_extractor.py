import urllib.parse

def extract_pdf_info(url):
    try:
        parsed_url = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed_url.path)
        filename = path.split("/")[-1]

        if not filename or '.' not in filename:
            filename = "document.pdf"

        supported_extensions = (
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.txt', '.csv', '.zip', '.rar', '.7z', '.tar', '.gz',
            '.apk', '.epub', '.json', '.xml', '.html', '.rtf'
        )

        if not filename.lower().endswith(supported_extensions):
            ext = filename.split('.')[-1] if '.' in filename else 'pdf'
            filename = f"document.{ext}"

        file_type = filename.split(".")[-1].lower()
        title = filename.replace("_", " ").replace("-", " ").title()

        return {
            "title": title,
            "file_url": url,
            "download_url": url,
            "file_type": file_type,
            "size": None
        }
    except Exception as e:
        print(f"Document extraction error: {e}")
        return {"title": "Document", "file_url": url, "download_url": url, "file_type": "unknown"}
import requests
from bs4 import BeautifulSoup

def extract_image_info(url):
    # 🌟 إضافة User-Agent متصفح حقيقي لتقليل فرص الحظر
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        # استخدام impersonate لمحاكاة متصفح كروم (يتطلب مكتبة curl_cffi)
        try:
            from curl_cffi import requests as curl_requests
            response = curl_requests.get(url, headers=headers, impersonate="chrome", timeout=10)
        except ImportError:
            # لو المكتبة مش موجودة، نرجع للطريقة العادية
            response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            raise Exception(f"Failed to fetch image page. Status: {response.status_code}")

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. محاولة البحث عن OpenGraph tags (أفضل جودة)
        og_image = soup.find("meta", property="og:image")
        image_url = og_image["content"] if og_image and "content" in og_image.attrs else None

        # 2. البحث عن meta twitter:image (بديل قوي)
        if not image_url:
            twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and "content" in twitter_image.attrs:
                image_url = twitter_image["content"]

        # 3. البحث عن أول صورة رئيسية في الصفحة
        if not image_url:
            img_tag = soup.find("img")
            if img_tag and "src" in img_tag.attrs:
                image_url = img_tag["src"]

        # 4. التأكد من أن الرابط مطلق (يبدأ بـ http)
        if image_url and image_url.startswith("//"):
            image_url = "https:" + image_url
        elif image_url and image_url.startswith("/"):
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            image_url = f"{parsed_url.scheme}://{parsed_url.netloc}{image_url}"

        # 5. لو ملقيناش صورة، نرجع الرابط الأصلي كحل أخير
        if not image_url:
            image_url = url

        title = soup.title.string.strip() if soup.title and soup.title.string else "Image Item"

        return {
            "title": title,
            "image_url": image_url,
            "direct_download_url": image_url
        }

    except Exception as e:
        print(f"Image extraction error: {e}")
        # 🌟 في حالة الفشل، نرجع بيانات أساسية بدل ما السيرفر ينهار
        return {
            "title": "Image",
            "image_url": url,
            "direct_download_url": url
        }

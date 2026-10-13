import requests
from bs4 import BeautifulSoup

def extract_image_info(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        raise Exception("Failed to fetch image page.")

    soup = BeautifulSoup(response.text, 'html.parser')

    # محاولة البحث عن الوسوم الشائعة للصور أو OpenGraph tags
    og_image = soup.find("meta", property="og:image")
    image_url = og_image["content"] if og_image and "content" in og_image.attrs else None

    if not image_url:
        # البحث عن أول صورة رئيسية في الصفحة كبديل
        img_tag = soup.find("img")
        image_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else url

    return {
        "title": soup.title.string if soup.title else "Image Item",
        "image_url": image_url,
        "direct_download_url": image_url
    }
formats = []
        best_url = None
        max_height = -1

        for f in info.get("formats", []):
            f_url = f.get("url")
            if not f_url:
                continue

            has_video = f.get("vcodec") != "none" and f.get("vcodec") is not None
            has_audio = f.get("acodec") != "none" and f.get("acodec") is not None
            height = f.get("height") or 0

            # نأخذ فقط الجودات التي تحتوي على فيديو وصوت معاً من المصدر
            if has_video and has_audio:
                item = {
                    "format_id": f.get("format_id"),
                    "url": f_url,
                    "ext": f.get("ext", "mp4"),
                    "height": height,
                    "quality": f"{height}p" if height > 0 else "standard",
                    "filesize": f.get("filesize") or f.get("filesize_approx") or 0,
                }
                formats.append(item)

                # اختيار أعلى جودة متاحة مدمجة تلقائياً
                if height >= max_height:
                    max_height = height
                    best_url = f_url

        if not best_url and formats:
            best_url = formats[0]["url"]
        elif not best_url:
            best_url = info.get("url")

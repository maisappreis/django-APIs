from urllib.parse import urlsplit, urlunsplit


SUPPORTED_LOCALES = {"pt", "en"}


def localize_frontend_url(url, locale, base_path="/axis"):
    """Add or replace the leading locale segment of a frontend URL."""
    if not url:
        return url

    locale = locale if locale in SUPPORTED_LOCALES else "pt"
    parsed = urlsplit(url)
    parts = [part for part in parsed.path.split("/") if part]
    base_parts = [part for part in base_path.split("/") if part]
    locale_index = 0

    if base_parts and parts[:len(base_parts)] == base_parts:
        locale_index = len(base_parts)

    if len(parts) > locale_index and parts[locale_index] in SUPPORTED_LOCALES:
        parts[locale_index] = locale
    else:
        parts.insert(locale_index, locale)

    path = "/" + "/".join(parts)
    if parsed.path.endswith("/"):
        path += "/"

    return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))

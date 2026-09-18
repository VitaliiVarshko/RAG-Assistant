# site_config.py
# Конфигурация для вашего сайта w34u.net

SITE_CONFIG = {
    "ru": {
        "url": "https://w34u.net/",
        "language": "ru",
        "max_pages": 100,  # Максимум страниц для сканирования
        # Какие страницы исключаем (например, технические)
        "exclude_patterns": [
            "/admin",
            "/login",
            "/register",
            "/cart",
            "/checkout",
            "/profile",
            "/search",
            "?",
            "#",
            "/index.php?route=",  # Технические URL OpenCart
            "user_token",
            "route=common/home"
        ],
        # Какие страницы обязательно сканируем (важные разделы)
        "include_patterns": [
            "/about-us",
            "/novosti",
            "/tseny",
            "/otzyvy-klientov",
            "/portfolio",
            "/blog",
            "/uslugi",
            "/1s-programmirovanie",
            "/sozdanie-sajtov",
            "/seo-prodvizhenie",
            "/it-autsorsing",
            "/sozdanie-internet-magazina",
            "/b2b-sistemy",
            "/sajt-v-kredit"
        ]
    },
    "uk": {
        "url": "https://w34u.net/ua/",
        "language": "uk",
        "max_pages": 100,
        "exclude_patterns": [
            "/admin",
            "/login",
            "/register",
            "/cart",
            "/checkout",
            "/profile",
            "/search",
            "?",
            "#",
            "/index.php?route=",
            "user_token",
            "route=common/home"
        ],
        "include_patterns": [
            "/about-us",
            "/novini",
            "/tsini",
            "/vidguki-klientiv",
            "/portfolio",
            "/blog",
            "/poslugi",
            "/1s-programuvannya",
            "/stvorennya-sajtiv",
            "/seo-prosuvannya",
            "/it-autsorsing",
            "/stvorennya-internet-magazinu",
            "/b2b-sistemi",
            "/sajt-u-kredit"
        ]
    }
}

# Настройки для извлечения контента
CONTENT_SELECTORS = {
    "main_content": [
        # Основной контент OpenCart обычно находится в этих блоках
        "#content",
        ".product-info",
        ".description",
        ".product-description",
        ".blog-description",
        ".news-description",
        ".article-content",
        "main",
        ".main-content",
        ".entry-content",
        ".page-content",
        # Добавляем селекторы для текстовых блоков
        ".col-sm-9", 
        ".col-md-9",
        ".col-lg-9"
    ],
    "title": [
        "h1",
        ".heading-title",
        ".page-title",
        ".product-title",
        ".blog-title",
        ".news-title",
        ".article-title"
    ],
    "exclude": [
        # Элементы, которые нужно исключить из текста
        "nav",
        "header",
        "footer",
        "aside",
        ".sidebar",
        ".menu",
        ".navigation",
        ".comments",
        ".advertisement",
        ".banner",
        ".popup",
        ".cookie-notice",
        ".buttons",  # Кнопки в OpenCart
        ".cart-info",
        ".product-options",
        ".product-stock",
        ".rating",
        ".product-layout",  # Может содержать повторяющиеся элементы
        ".product-thumb"     # Может содержать повторяющиеся элементы
    ]
}
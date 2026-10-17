"""Módulo de tópicos, operadores de busca e suporte multilíngue para IA."""

from typing import Any

# Lista oficial dos 20 maiores idiomas (Lote 1 - que cabem em uma única query de até 512 caracteres)
TOP_20_LANG_CODES: list[str] = [
    "en",
    "pt",
    "es",
    "fr",
    "de",
    "it",
    "ja",
    "zh",
    "ru",
    "ar",
    "ko",
    "hi",
    "tr",
    "nl",
    "pl",
    "vi",
    "id",
    "th",
    "sv",
    "uk",
]

# Query consolidada unificada pronta dos 20 maiores idiomas (508 caracteres)
TOP_20_CONSOLIDATED_QUERY: str = (
    '(#AI OR #IA OR #GenAI OR "artificial intelligence" OR '
    '"inteligência artificial" OR "inteligencia artificial" OR '
    '"intelligence artificielle" OR "künstliche intelligenz" OR '
    '"intelligenza artificiale" OR "人工知能" OR "人工智能" OR '
    '"искусственный интеллект" OR "الذكاء الاصطناعي" OR "인공지능" OR '
    '"आर्टिफिशियल इंटेलिजेंस" OR "yapay zeka" OR "kunstmatige intelligentie" OR '
    '"sztuczna inteligencja" OR "trí tuệ nhân tạo" OR "kecerdasan buatan" OR '
    '"ปัญญาประดิษฐ์" OR "artificiell intelligens" OR "штучний інтелект") -is:retweet'
)

# Catálogo completo de termos de busca de IA para 32 idiomas
AI_TERMS_BY_LANGUAGE: dict[str, dict[str, Any]] = {
    # --- LOTE 1: OS 20 MAIORES IDIOMAS ---
    "en": {
        "name": "Inglês",
        "batch": 1,
        "is_top20": True,
        "query": '("artificial intelligence" OR #AI OR #ArtificialIntelligence OR "generative AI" OR #GenAI OR "LLM")',
    },
    "pt": {
        "name": "Português",
        "batch": 1,
        "is_top20": True,
        "query": '("inteligência artificial" OR "inteligencia artificial" OR #IA OR #InteligenciaArtificial OR "IA generativa" OR "modelo de IA")',
    },
    "es": {
        "name": "Espanhol",
        "batch": 1,
        "is_top20": True,
        "query": '("inteligencia artificial" OR #IA OR #InteligenciaArtificial OR "IA generativa" OR "modelo de IA")',
    },
    "fr": {
        "name": "Francês",
        "batch": 1,
        "is_top20": True,
        "query": '("intelligence artificielle" OR #IA OR #IntelligenceArtificielle OR "IA générative")',
    },
    "de": {
        "name": "Alemão",
        "batch": 1,
        "is_top20": True,
        "query": '("künstliche intelligenz" OR "kuenstliche intelligenz" OR #KI OR #KuenstlicheIntelligenz OR #AI)',
    },
    "it": {
        "name": "Italiano",
        "batch": 1,
        "is_top20": True,
        "query": '("intelligenza artificiale" OR #IA OR #IntelligenzaArtificiale OR "IA generativa")',
    },
    "ja": {
        "name": "Japonês",
        "batch": 1,
        "is_top20": True,
        "query": '("人工知能" OR "生成AI" OR "AIモデル" OR #AI OR #人工知能)',
    },
    "zh": {
        "name": "Chinês",
        "batch": 1,
        "is_top20": True,
        "query": '("人工智能" OR "生成式AI" OR "大语言模型" OR #AI OR #人工智能)',
    },
    "ru": {
        "name": "Russo",
        "batch": 1,
        "is_top20": True,
        "query": '("искусственный интеллект" OR "генеративный ИИ" OR #ИИ OR #AI)',
    },
    "ar": {
        "name": "Árabe",
        "batch": 1,
        "is_top20": True,
        "query": '("الذكاء الاصطناعي" OR "ذكاء اصطناعي" OR #الذكاء_الاصطناعي OR #ذكاء_اصطناعي)',
    },
    "ko": {
        "name": "Coreano",
        "batch": 1,
        "is_top20": True,
        "query": '("인공지능" OR "생성형 AI" OR "생성형AI" OR #AI OR #인공지능)',
    },
    "hi": {
        "name": "Hindi",
        "batch": 1,
        "is_top20": True,
        "query": '("आर्टिफिशियल इंटेलिजेंस" OR "कृत्रिम बुद्धिमत्ता" OR #AI)',
    },
    "tr": {
        "name": "Turco",
        "batch": 1,
        "is_top20": True,
        "query": '("yapay zeka" OR "yapay zekâ" OR #YapayZeka OR #AI)',
    },
    "nl": {
        "name": "Holandês",
        "batch": 1,
        "is_top20": True,
        "query": '("kunstmatige intelligentie" OR "generatieve AI" OR #AI)',
    },
    "pl": {
        "name": "Polonês",
        "batch": 1,
        "is_top20": True,
        "query": '("sztuczna inteligencja" OR "generatywna AI" OR #AI OR #SztucznaInteligencja)',
    },
    "vi": {
        "name": "Vietnamita",
        "batch": 1,
        "is_top20": True,
        "query": '("trí tuệ nhân tạo" OR "trí thông minh nhân tạo" OR #AI)',
    },
    "id": {
        "name": "Indonésio",
        "batch": 1,
        "is_top20": True,
        "query": '("kecerdasan buatan" OR "AI generatif" OR #AI)',
    },
    "th": {
        "name": "Tailandês",
        "batch": 1,
        "is_top20": True,
        "query": '("ปัญญาประดิษฐ์" OR #ปัญญาประดิษฐ์ OR #AI)',
    },
    "sv": {
        "name": "Sueco",
        "batch": 1,
        "is_top20": True,
        "query": '("artificiell intelligens" OR #AI)',
    },
    "uk": {
        "name": "Ucraniano",
        "batch": 1,
        "is_top20": True,
        "query": '("штучний інтелект" OR #ШІ OR #AI)',
    },
    # --- LOTE 2: OUTROS IDIOMAS SECUNDÁRIOS ---
    "el": {
        "name": "Grego",
        "batch": 2,
        "is_top20": False,
        "query": '("τεχνητή νοημοσύνη" OR #τεχνητή_νοημοσύνη OR #AI)',
    },
    "he": {
        "name": "Hebraico",
        "batch": 2,
        "is_top20": False,
        "query": '("בינה מלאכותית" OR #בינה_מלאכותית OR #AI)',
    },
    "cs": {
        "name": "Tcheco",
        "batch": 2,
        "is_top20": False,
        "query": '("umělá inteligence" OR #umelainteligence OR #AI)',
    },
    "ro": {
        "name": "Romeno",
        "batch": 2,
        "is_top20": False,
        "query": '("inteligență artificială" OR "inteligenta artificiala" OR #IA OR #AI)',
    },
    "hu": {
        "name": "Húngaro",
        "batch": 2,
        "is_top20": False,
        "query": '("mesterséges intelligencia" OR #AI)',
    },
    "da": {
        "name": "Dinamarquês",
        "batch": 2,
        "is_top20": False,
        "query": '("kunstig intelligens" OR #AI)',
    },
    "fi": {
        "name": "Finlandês",
        "batch": 2,
        "is_top20": False,
        "query": '("tekoäly" OR "generatiivinen tekoäly" OR #tekoäly OR #AI)',
    },
    "no": {
        "name": "Norueguês",
        "batch": 2,
        "is_top20": False,
        "query": '("kunstig intelligens" OR #AI)',
    },
    "tl": {
        "name": "Tagalo (Filipino)",
        "batch": 2,
        "is_top20": False,
        "query": '("artipisyal na katalinuhan" OR #AI)',
    },
    "fa": {
        "name": "Persa (Farsi)",
        "batch": 2,
        "is_top20": False,
        "query": '("هوش مصنوعی" OR #هوش_مصنوعی OR #AI)',
    },
    "ur": {
        "name": "Urdu",
        "batch": 2,
        "is_top20": False,
        "query": '("مصنوعی ذہانت" OR #AI)',
    },
    "bn": {
        "name": "Bengali",
        "batch": 2,
        "is_top20": False,
        "query": '("কৃত্রিম বুদ্ধিমত্তা" OR #AI)',
    },
}

MAX_QUERY_LENGTH = 512


def build_ai_query(lang: str | None = "pt", exclude_retweets: bool = True) -> str:
    """
    Constrói uma query completa e otimizada de IA para um idioma específico.
    Garante que não ultrapasse o limite de 512 caracteres da API v2.
    """
    if lang and lang in AI_TERMS_BY_LANGUAGE:
        base = AI_TERMS_BY_LANGUAGE[lang]["query"]
        lang_filter = f" lang:{lang}"
    else:
        # Padrão internacional (Inglês + Espanhol + Português compacto)
        base = '("artificial intelligence" OR "inteligência artificial" OR "inteligencia artificial" OR #AI OR #IA)'
        lang_filter = f" lang:{lang}" if lang else ""

    retweet_filter = " -is:retweet" if exclude_retweets else ""
    full_query = f"{base}{lang_filter}{retweet_filter}"

    if len(full_query) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"Query excede o limite máximo de {MAX_QUERY_LENGTH} caracteres da API do X: ({len(full_query)} chars)"
        )

    return full_query


def list_available_languages(only_top20: bool = False) -> list[dict[str, Any]]:
    """Retorna a lista dos idiomas suportados, marcando quem é Top 20 (Lote 1)."""
    items = []
    for code, info in AI_TERMS_BY_LANGUAGE.items():
        if only_top20 and not info.get("is_top20", False):
            continue
        items.append(
            {
                "code": code,
                "name": info["name"],
                "batch": info.get("batch", 1),
                "is_top20": info.get("is_top20", False),
                "terms": info["query"],
            }
        )
    return items


def get_multilingual_batches(max_chars: int = 512, exclude_retweets: bool = True) -> list[dict[str, Any]]:
    """
    Agrupa os idiomas em lotes de queries consolidadas que cabem no limite de caracteres da API.
    Lote 1 contém os 20 maiores idiomas (506 chars).
    Lote 2 contém os outros 12 idiomas (286 chars).
    """
    suffix = " -is:retweet" if exclude_retweets else ""

    # Lote 1: Top 20 idiomas + hashtags globais
    lote1_terms = [
        "#AI",
        "#IA",
        "#GenAI",
        '"artificial intelligence"',
        '"inteligência artificial"',
        '"inteligencia artificial"',
        '"intelligence artificielle"',
        '"künstliche intelligenz"',
        '"intelligenza artificiale"',
        '"人工知能"',
        '"人工智能"',
        '"искусственный интеллект"',
        '"الذكاء الاصطناعي"',
        '"인공지능"',
        '"आर्टिफिशियल इंटेलिजेंस"',
        '"yapay zeka"',
        '"kunstmatige intelligentie"',
        '"sztuczna inteligencja"',
        '"trí tuệ nhân tạo"',
        '"kecerdasan buatan"',
        '"ปัญญาประดิษฐ์"',
        '"artificiell intelligens"',
        '"штучний інтелект"',
    ]
    query_lote1 = " OR ".join(lote1_terms) + suffix

    # Lote 2: Outros 12 idiomas
    lote2_terms = [
        '"τεχνητή νοημοσύνη"',
        '"בינה מלאכותית"',
        '"umělá inteligence"',
        '"inteligență artificială"',
        '"mesterséges intelligencia"',
        '"kunstig intelligens"',
        '"tekoäly"',
        '"artipisyal na katalinuhan"',
        '"هوش مصنوعی"',
        '"مصنوعی ذہانت"',
        '"কৃত্রিম বুদ্ধিমত্তা"',
    ]
    query_lote2 = " OR ".join(lote2_terms) + suffix

    return [
        {
            "batch_id": 1,
            "name": "Lote 1 (Top 20 Maiores Idiomas + Hashtags)",
            "query": query_lote1,
            "char_length": len(query_lote1),
            "languages": [{"code": c, "name": AI_TERMS_BY_LANGUAGE[c]["name"]} for c in TOP_20_LANG_CODES],
        },
        {
            "batch_id": 2,
            "name": "Lote 2 (12 Idiomas Secundários)",
            "query": query_lote2,
            "char_length": len(query_lote2),
            "languages": [
                {"code": c, "name": data["name"]}
                for c, data in AI_TERMS_BY_LANGUAGE.items()
                if not data.get("is_top20", False)
            ],
        },
    ]

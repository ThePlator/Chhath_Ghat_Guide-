"""UI strings per language (LLD §5, HLD §8.6).

Hindi is complete. Bhojpuri / Maithili entries are drafts to be checked by a
native speaker; any missing key falls back to Hindi.
"""

from __future__ import annotations

FALLBACK = "hi"

LANGUAGE_LABELS = {"hi": "हिन्दी", "bho": "भोजपुरी (β)", "mai": "मैथिली (β)"}

STRINGS: dict[str, dict[str, str]] = {
    "hi": {
        "app_title": "छठ घाट गाइड",
        "app_tagline": "बिना इंटरनेट के घाट पर परिवार का साथी",
        "language_label": "भाषा",
        "beta_note": "भोजपुरी और मैथिली अभी परीक्षण में हैं; कुछ शब्द हिन्दी में आ सकते हैं।",
        "tab_notice": "📜 सूचना पढ़ें",
        "tab_ritual": "🪔 पूजा सहायक",
        "tab_meeting": "📍 मिलने की जगह",
        "emergency_title": "🆘 आपात स्थिति",
        "emergency_default": "किसी भी परेशानी में सबसे पास के पुलिस या स्वयंसेवक बूथ पर जाएँ।",
        "emergency_contacts": "स्थानीय संपर्क",
        "helper_note": "यह ऐप केवल सहायक है। सरकारी घोषणा, पुलिस, स्वयंसेवक और घर के बड़े पहले हैं।",
        "health_server_down": "मॉडल चालू नहीं है। लैपटॉप पर `ollama serve` चलाएँ, फिर पेज दोबारा खोलें।",
        "health_model_missing": "मॉडल नहीं मिला। लैपटॉप पर चलाएँ: {cmds}",
        "health_meeting_ok": "मिलने की जगह वाला हिस्सा फिर भी काम करेगा।",
        "notice_intro": "किसी सूचना, बैनर या बोर्ड की फोटो लें। ऐप उसे पढ़कर आसान भाषा में समझाएगा।",
        "take_photo": "फोटो लें",
        "upload_photo": "फोटो लें या गैलरी से चुनें",
        "use_camera": "📷 इसी पेज पर कैमरा खोलें",
        "reading": "सूचना पढ़ रहे हैं… लैपटॉप पर इसमें एक-दो मिनट लग सकते हैं। दूसरे फोन भी पूछ रहे हों तो थोड़ा और।",
        "explaining": "आसान भाषा में समझा रहे हैं…",
        "unclear_title": "साफ़ नहीं पढ़ पाए",
        "unclear_tips": "पास जाकर, सीधे सामने से, चमक से बचाकर और फोन स्थिर रखकर दोबारा फोटो लें।",
        "unclear_partial_text": "जितना पढ़ पाए:",
        "partial_note": "कुछ शब्द साफ़ नहीं पढ़े गए ([?] से दिखाए गए हैं)। मूल सूचना ज़रूर देखें।",
        "safety_title": "⚠️ सुरक्षा सूचना — मूल लिखा हुआ पहले पढ़ें",
        "explanation_title": "आसान भाषा में",
        "original_text": "सूचना में जो लिखा है",
        "check_numbers": "समझाने में कुछ अंक ({nums}) आए हैं जो सूचना में नहीं मिले। समय और घाट नंबर मूल सूचना से ही मिलाएँ।",
        "explain_failed": "समझाने में दिक्कत हुई। ऊपर लिखी मूल सूचना पढ़ें या किसी से पूछें।",
        "notice_disclaimer": "सरकारी घोषणा और स्वयंसेवकों की बात सबसे पहले मानें।",
        "photo_shown": "भेजी गई फोटो",
        "err_timeout": "बहुत समय लग रहा है। पास से, साफ़ और छोटी फोटो लेकर दोबारा कोशिश करें।",
        "err_image": "फोटो खुल नहीं पाई। JPG या PNG फोटो चुनें।",
        "err_generic": "कुछ गड़बड़ हुई। दोबारा कोशिश करें।",
        "err_unavailable": "मॉडल से नहीं जुड़ पाए। लैपटॉप पर Ollama चालू है और मॉडल डाउनलोड है, यह जाँचें।",
        "ritual_intro": "छठ पूजा के बारे में सवाल पूछें। जवाब सिर्फ़ उन नोट्स से आता है जिन्हें घर के बड़ों ने जाँचा है।",
        "ritual_question": "आपका सवाल",
        "ritual_placeholder": "जैसे: अर्घ्य कब दिया जाता है?",
        "ritual_ask": "पूछें",
        "ritual_examples": "या इनमें से चुनें",
        "ritual_thinking": "नोट्स में देख रहे हैं…",
        "ritual_empty_question": "कृपया सवाल लिखें।",
        "not_in_notes": "🙏 यह मेरे नोट्स में नहीं है। कृपया घर के किसी बड़े से पूछें।",
        "official_info": "🕰️ समय, तारीख और घाट की व्यवस्था मेरे नोट्स में नहीं है। इसके लिए सरकारी सूचना, पंचांग या स्वयंसेवकों से पूछें।",
        "customs_vary": "हर परिवार और इलाके के रिवाज़ थोड़े अलग होते हैं; अपने घर का तरीका बड़ों से पूछें।",
        "sources": "यह जवाब किन नोट्स से आया",
        "checked_by_line": "जाँचा: {who}, {when}",
        "ritual_no_notes": "अभी कोई नोट जाँचा नहीं गया है, इसलिए पूजा सहायक बंद है। kb/ फ़ोल्डर के नोट्स किसी बड़े को पढ़कर सुनाएँ और checked_by भरें (kb/README.md देखें)।",
        "ritual_index_error": "नोट्स तैयार नहीं हो पाए। लैपटॉप पर Ollama और `nomic-embed-text` मॉडल जाँचें।",
        "ritual_recent": "पिछले सवाल",
        "coming_soon_meeting": "मिलने की जगह जल्द आ रही है।",
    },
    "bho": {
        "app_tagline": "बिना इंटरनेट के घाट पर परिवार के साथी",
        "tab_notice": "📜 सूचना पढ़ीं",
        "ritual_question": "रउआ के सवाल",
        "unclear_title": "साफ़ ना पढ़ पवनी",
        "explanation_title": "आसान भाषा में",
        "original_text": "सूचना में जवन लिखल बा",
    },
    "mai": {
        "app_tagline": "बिना इंटरनेटक घाट पर परिवारक संगी",
        "tab_notice": "📜 सूचना पढ़ू",
        "ritual_question": "अहाँक प्रश्न",
        "unclear_title": "साफ़ नहि पढ़ि सकलहुँ",
        "explanation_title": "सरल भाषा मे",
        "original_text": "सूचना मे जे लिखल अछि",
    },
}


def t(key: str, lang: str = FALLBACK, **fmt) -> str:
    table = STRINGS.get(lang, {})
    text = table.get(key) or STRINGS[FALLBACK].get(key)
    if text is None:
        raise KeyError(f"missing UI string {key!r}")
    return text.format(**fmt) if fmt else text


RITUAL_EXAMPLES: dict[str, list[str]] = {
    "hi": [
        "अर्घ्य कब दिया जाता है?",
        "सूप में क्या रखते हैं?",
        "खरना में क्या बनता है?",
        "नहाय-खाय में क्या खाते हैं?",
        "ठेकुआ कैसे बनता है?",
        "निर्जला व्रत कब शुरू होता है?",
    ],
}


def ritual_examples(lang: str) -> list[str]:
    return RITUAL_EXAMPLES.get(lang) or RITUAL_EXAMPLES[FALLBACK]

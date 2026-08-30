# -*- coding: utf-8 -*-
"""نقشه‌ی هم‌مرزی کشورهای بازی.

مرزهای زمینی واقعی (و در چند مورد، مرز دریایی نزدیک که در عمل مثل هم‌مرزی
عمل می‌کند، مثل ژاپن–کره جنوبی یا اندونزی–استرالیا).

فقط کشورهایی که در بازی وجود دارند فهرست شده‌اند؛ همسایه‌هایی که در بازی
نیستند حذف شده‌اند. رابطه دوطرفه است و در زمان بارگذاری متقارن می‌شود.
"""

_RAW_BORDERS = {
    # ── خاورمیانه ──
    "iran": ["iraq", "turkey", "armenia", "azerbaijan", "turkmenistan", "afghanistan", "pakistan"],
    "iraq": ["iran", "turkey", "syria", "jordan", "saudi", "kuwait", "kurdistan"],
    "kurdistan": ["iraq", "iran", "turkey", "syria"],
    "syria": ["turkey", "iraq", "jordan", "israel", "lebanon", "hezbollah"],
    "lebanon": ["syria", "israel", "hezbollah"],
    "hezbollah": ["lebanon", "syria", "israel"],
    "israel": ["lebanon", "syria", "jordan", "egypt", "palestine"],
    "palestine": ["israel", "egypt", "jordan"],
    "jordan": ["syria", "iraq", "saudi", "israel", "palestine"],
    "saudi": ["iraq", "jordan", "kuwait", "qatar", "uae", "oman", "yemen", "bahrain"],
    "kuwait": ["iraq", "saudi"],
    "qatar": ["saudi", "uae", "bahrain"],
    "bahrain": ["saudi", "qatar"],
    "uae": ["saudi", "oman", "qatar"],
    "oman": ["uae", "saudi", "yemen"],
    "yemen": ["saudi", "oman", "somalia", "eritrea"],
    "turkey": ["iran", "iraq", "syria", "georgia", "armenia", "azerbaijan", "greece", "bulgaria", "cyprus", "kurdistan"],
    "cyprus": ["turkey", "greece"],
    "armenia": ["turkey", "iran", "georgia", "azerbaijan"],
    "azerbaijan": ["iran", "turkey", "georgia", "armenia", "russia"],
    "georgia": ["russia", "turkey", "armenia", "azerbaijan"],
    "egypt": ["libya", "sudan", "israel", "palestine"],

    # ── آسیای مرکزی و جنوبی ──
    "afghanistan": ["iran", "pakistan", "turkmenistan", "uzbekistan", "tajikistan", "china"],
    "pakistan": ["iran", "afghanistan", "india", "china"],
    "india": ["pakistan", "china", "nepal", "bangladesh", "myanmar", "sri_lanka"],
    "nepal": ["india", "china"],
    "bangladesh": ["india", "myanmar"],
    "sri_lanka": ["india"],
    "turkmenistan": ["iran", "afghanistan", "uzbekistan", "kazakhstan"],
    "uzbekistan": ["afghanistan", "turkmenistan", "kazakhstan", "kyrgyzstan", "tajikistan"],
    "tajikistan": ["afghanistan", "uzbekistan", "kyrgyzstan", "china"],
    "kyrgyzstan": ["kazakhstan", "uzbekistan", "tajikistan", "china"],
    "kazakhstan": ["russia", "china", "kyrgyzstan", "uzbekistan", "turkmenistan"],
    "mongolia": ["russia", "china"],

    # ── شرق و جنوب شرق آسیا ──
    "china": ["russia", "mongolia", "north_korea", "kazakhstan", "kyrgyzstan", "tajikistan",
              "afghanistan", "pakistan", "india", "nepal", "myanmar", "laos", "vietnam", "taiwan"],
    "north_korea": ["china", "russia", "south_korea"],
    "south_korea": ["north_korea", "japan"],
    "japan": ["south_korea", "russia", "taiwan"],
    "taiwan": ["china", "japan", "philippines"],
    "myanmar": ["china", "india", "bangladesh", "thailand", "laos"],
    "thailand": ["myanmar", "laos", "cambodia", "malaysia"],
    "laos": ["china", "myanmar", "thailand", "cambodia", "vietnam"],
    "cambodia": ["thailand", "laos", "vietnam"],
    "vietnam": ["china", "laos", "cambodia"],
    "malaysia": ["thailand", "singapore", "indonesia"],
    "singapore": ["malaysia", "indonesia"],
    "indonesia": ["malaysia", "singapore", "philippines", "australia"],
    "philippines": ["taiwan", "indonesia"],
    "australia": ["indonesia", "new_zealand"],
    "new_zealand": ["australia"],

    # ── اروپا ──
    "russia": ["norway", "finland", "belarus", "ukraine", "georgia", "azerbaijan",
               "kazakhstan", "mongolia", "china", "north_korea", "japan", "poland"],
    "ukraine": ["russia", "belarus", "poland", "slovakia", "hungary", "romania"],
    "belarus": ["russia", "ukraine", "poland"],
    "poland": ["germany", "czech", "slovakia", "ukraine", "belarus", "russia"],
    "germany": ["france", "belgium", "netherlands", "denmark", "poland", "czech", "austria", "switzerland"],
    "france": ["spain", "belgium", "germany", "switzerland", "italy", "uk"],
    "spain": ["france", "portugal", "morocco"],
    "portugal": ["spain"],
    "italy": ["france", "switzerland", "austria", "croatia", "greece"],
    "switzerland": ["france", "germany", "austria", "italy"],
    "austria": ["germany", "czech", "slovakia", "hungary", "croatia", "italy", "switzerland"],
    "czech": ["germany", "poland", "slovakia", "austria"],
    "slovakia": ["czech", "poland", "ukraine", "hungary", "austria"],
    "hungary": ["slovakia", "ukraine", "romania", "serbia", "croatia", "austria"],
    "romania": ["ukraine", "hungary", "serbia", "bulgaria"],
    "bulgaria": ["romania", "serbia", "greece", "turkey"],
    "serbia": ["hungary", "romania", "bulgaria", "croatia"],
    "croatia": ["hungary", "serbia", "italy", "austria"],
    "greece": ["bulgaria", "turkey", "cyprus", "italy"],
    "netherlands": ["germany", "belgium", "uk"],
    "belgium": ["france", "germany", "netherlands", "uk"],
    "denmark": ["germany", "sweden", "norway"],
    "norway": ["sweden", "finland", "russia", "denmark"],
    "sweden": ["norway", "finland", "denmark"],
    "finland": ["norway", "sweden", "russia"],
    "uk": ["france", "belgium", "netherlands"],

    # ── آفریقا ──
    "libya": ["egypt", "sudan", "tunisia", "algeria"],
    "tunisia": ["libya", "algeria"],
    "algeria": ["tunisia", "libya", "morocco"],
    "morocco": ["algeria", "spain"],
    "sudan": ["egypt", "libya", "eritrea", "ethiopia"],
    "eritrea": ["sudan", "ethiopia", "yemen"],
    "ethiopia": ["sudan", "eritrea", "somalia", "kenya"],
    "somalia": ["ethiopia", "kenya", "yemen"],
    "kenya": ["ethiopia", "somalia"],
    "nigeria": [],
    "angola": [],
    "south_africa": [],

    # ── آمریکا ──
    "usa": ["canada", "mexico", "cuba"],
    "canada": ["usa"],
    "mexico": ["usa", "cuba"],
    "cuba": ["usa", "mexico"],
    "venezuela": ["colombia", "brazil"],
    "colombia": ["venezuela", "brazil", "ecuador", "peru"],
    "ecuador": ["colombia", "peru"],
    "peru": ["ecuador", "colombia", "brazil", "bolivia", "chile"],
    "bolivia": ["peru", "brazil", "chile", "argentina"],
    "brazil": ["venezuela", "colombia", "peru", "bolivia", "argentina"],
    "argentina": ["brazil", "bolivia", "chile"],
    "chile": ["peru", "bolivia", "argentina"],
}


def build_border_map(valid_keys) -> dict:
    """نقشه‌ی متقارن هم‌مرزی، محدود به کشورهایی که واقعاً در بازی هستند."""
    valid = set(valid_keys)
    borders = {key: set() for key in valid}
    for country, neighbours in _RAW_BORDERS.items():
        if country not in valid:
            continue
        for neighbour in neighbours:
            if neighbour in valid and neighbour != country:
                borders[country].add(neighbour)
                borders[neighbour].add(country)
    return {key: sorted(value) for key, value in borders.items()}


# ══════════════════════════ نقشه‌ی خالص زمینی (ترابری زمینی) ══════════════════════════
#
# نقشه‌ی عملیاتی بالا چند پیوند «دریایی-نزدیک» دارد که در رول‌پلی مثل هم‌مرزی
# حساب می‌شوند اما هیچ گذرگاه زمینی/ریلی واقعی ندارند (کامیون و قطار نمی‌توانند
# از آن‌ها عبور کنند). این جفت‌ها برای ترابری زمینی حذف می‌شوند.
#
# گذرگاه‌های مصنوعیِ واقعی آگاهانه به‌عنوان زمینی حفظ شده‌اند:
#   uk–france (تونل مانش)، denmark–sweden (پل اورسوند)،
#   saudi–bahrain (گذرگاه ملک فهد)، malaysia–singapore (گذرگاه جوهر).
_NEAR_SEA_LINKS = {
    frozenset(pair)
    for pair in {
        # خاورمیانه و دریای سرخ
        ("turkey", "cyprus"),
        ("cyprus", "greece"),
        ("qatar", "bahrain"),
        ("yemen", "somalia"),
        ("yemen", "eritrea"),
        # جنوب و شرق آسیا
        ("india", "sri_lanka"),
        ("china", "taiwan"),
        ("taiwan", "japan"),
        ("taiwan", "philippines"),
        ("philippines", "indonesia"),
        ("south_korea", "japan"),
        ("japan", "russia"),
        ("malaysia", "indonesia"),
        ("singapore", "indonesia"),
        ("indonesia", "australia"),
        ("australia", "new_zealand"),
        # اروپا و مدیترانه
        ("italy", "croatia"),
        ("italy", "greece"),
        ("denmark", "norway"),
        ("uk", "belgium"),
        ("uk", "netherlands"),
        ("spain", "morocco"),
        # آمریکا و کارائیب
        ("usa", "cuba"),
        ("mexico", "cuba"),
    }
}


def build_land_route_map(valid_keys) -> dict:
    """نقشه‌ی هم‌مرزی «خالص زمینی»؛ پیوندهای دریایی-نزدیک حذف شده‌اند.

    این نقشه برای ترابری زمینی (کامیون/قطار) استفاده می‌شود و با build_border_map
    (که پیوندهای رول‌پلی دریایی را هم دارد) متفاوت است.
    """
    valid = set(valid_keys)
    land = {key: set() for key in valid}
    for country, neighbours in _RAW_BORDERS.items():
        if country not in valid:
            continue
        for neighbour in neighbours:
            if neighbour not in valid or neighbour == country:
                continue
            if frozenset((country, neighbour)) in _NEAR_SEA_LINKS:
                continue
            land[country].add(neighbour)
            land[neighbour].add(country)
    return {key: sorted(value) for key, value in land.items()}


_LAND_COMPONENTS_CACHE: dict = {}


def land_route_components(valid_keys) -> dict:
    """برچسب مؤلفه‌ی همبندی خشکی هر کشور؛ دو کشور با برچسب برابر مسیر زمینی دارند.

    نتیجه بر اساس فهرست کشورها کش می‌شود (کاتالوگ کشورها در طول اجرا ثابت است).
    """
    signature = tuple(sorted(valid_keys))
    cached = _LAND_COMPONENTS_CACHE.get(signature)
    if cached is not None:
        return cached
    land_map = build_land_route_map(valid_keys)
    components: dict = {}
    component_id = 0
    for key in land_map:
        if key in components:
            continue
        stack = [key]
        components[key] = component_id
        while stack:
            current = stack.pop()
            for neighbour in land_map.get(current, ()):
                if neighbour not in components:
                    components[neighbour] = component_id
                    stack.append(neighbour)
        component_id += 1
    _LAND_COMPONENTS_CACHE[signature] = components
    return components


def has_land_route(country_key_a: str, country_key_b: str, valid_keys) -> bool:
    """آیا زنجیره‌ای پیوسته از خشکی (مرز مستقیم یا ترانزیت خاکی) بین دو کشور هست؟"""
    if not country_key_a or not country_key_b or country_key_a == country_key_b:
        return False
    components = land_route_components(valid_keys)
    component_a = components.get(country_key_a)
    component_b = components.get(country_key_b)
    return component_a is not None and component_a == component_b

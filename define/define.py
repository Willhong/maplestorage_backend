# import os
# from dotenv import load_dotenv

# load_dotenv()
# BASE_URL = "https://open.api.nexon.com/maplestory/v1"
# APIKEY = os.getenv("MAPLESTORY_API_KEY")

import os
BASE_URL = "https://open.api.nexon.com/maplestory/v1"
APIKEY = "test_4468fa7dc351c4fc07584a17f0b664d4ef5267515c18bc96e3db4c225b7f8789cb6dfb7e3b98213ec2b17da60c255a43"

# API Endpoints
CHARACTER_ID_URL = f"{BASE_URL}/id"
CHARACTER_BASIC_URL = f"{BASE_URL}/character/basic"
CHARACTER_POPULARITY_URL = f"{BASE_URL}/character/popularity"
CHARACTER_STAT_URL = f"{BASE_URL}/character/stat"
CHARACTER_ABILITY_URL = f"{BASE_URL}/character/ability"
CHARACTER_ITEM_EQUIPMENT_URL = f"{BASE_URL}/character/item-equipment"
CHARACTER_CASHITEM_EQUIPMENT_URL = f"{BASE_URL}/character/cashitem-equipment"
CHARACTER_SYMBOL_URL = f"{BASE_URL}/character/symbol-equipment"
CHARACTER_LINK_SKILL_URL = f"{BASE_URL}/character/link-skill"
CHARACTER_SKILL_URL = f"{BASE_URL}/character/skill"
CHARACTER_HEXAMATRIX_URL = f"{BASE_URL}/character/hexamatrix"
CHARACTER_HEXAMATRIX_STAT_URL = f"{BASE_URL}/character/hexamatrix-stat"

CHARACTER_VMATRIX_URL = f"{BASE_URL}/character/vmatrix"
CHARACTER_DOJANG_URL = f"{BASE_URL}/character/dojang"
CHARACTER_SET_EFFECT_URL = f"{BASE_URL}/character/set-effect"
CHARACTER_BEAUTY_EQUIPMENT_URL = f"{BASE_URL}/character/beauty-equipment"
CHARACTER_ANDROID_EQUIPMENT_URL = f"{BASE_URL}/character/android-equipment"
CHARACTER_PET_EQUIPMENT_URL = f"{BASE_URL}/character/pet-equipment"
CHARACTER_PROPENSITY_URL = f"{BASE_URL}/character/propensity"
CHARACTER_HYPER_STAT_URL = f"{BASE_URL}/character/hyper-stat"

"""
실제 Nexon API를 호출하여 테스트 fixture JSON 파일 생성
Story 2.11: API View 테스트 리팩토링
"""
import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

BASE_URL = "https://open.api.nexon.com/maplestory/v1"
APIKEY = os.getenv("MAPLESTORY_API_KEY")

# Fixtures 저장 경로
FIXTURES_DIR = Path(__file__).parent / "characters" / "tests" / "fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

# 테스트 캐릭터명
CHARACTER_NAME = "식사동그놈"


def get_headers():
    return {
        "accept": "application/json",
        "x-nxopen-api-key": APIKEY
    }


def fetch_and_save(endpoint: str, params: dict, filename: str):
    """API 호출 후 JSON 파일로 저장"""
    url = f"{BASE_URL}/{endpoint}"
    print(f"Fetching: {url} with params: {params}")

    try:
        response = requests.get(url, headers=get_headers(), params=params)
        response.raise_for_status()
        data = response.json()

        filepath = FIXTURES_DIR / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Saved: {filepath}")
        return data
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching {endpoint}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return None


def main():
    print(f"=== Generating fixtures for character: {CHARACTER_NAME} ===")
    print(f"API Key: {APIKEY[:20]}..." if APIKEY else "API Key not found!")

    if not APIKEY:
        print("Error: MAPLESTORY_API_KEY not set in .env file")
        return

    # 1. OCID 조회
    print("\n1. Fetching character ID (OCID)...")
    ocid_data = fetch_and_save("id", {"character_name": CHARACTER_NAME}, "character_id.json")

    if not ocid_data or "ocid" not in ocid_data:
        print("Failed to get OCID. Stopping.")
        return

    ocid = ocid_data["ocid"]
    print(f"   OCID: {ocid}")

    # 2. 기본 정보 조회
    print("\n2. Fetching character basic info...")
    fetch_and_save("character/basic", {"ocid": ocid}, "character_basic.json")

    # 3. 스탯 정보 조회
    print("\n3. Fetching character stat info...")
    fetch_and_save("character/stat", {"ocid": ocid}, "character_stat.json")

    # 4. 인기도 조회
    print("\n4. Fetching character popularity...")
    fetch_and_save("character/popularity", {"ocid": ocid}, "character_popularity.json")

    # 5. 장비 정보 조회
    print("\n5. Fetching item equipment info...")
    fetch_and_save("character/item-equipment", {"ocid": ocid}, "item_equipment.json")

    # 6. 전체 데이터용 추가 정보들 (선택적)
    print("\n6. Fetching additional data for character_all_data...")

    # Ability
    ability_data = fetch_and_save("character/ability", {"ocid": ocid}, "character_ability.json")

    # Propensity
    propensity_data = fetch_and_save("character/propensity", {"ocid": ocid}, "character_propensity.json")

    # Hyper Stat
    hyper_stat_data = fetch_and_save("character/hyper-stat", {"ocid": ocid}, "character_hyper_stat.json")

    print("\n=== Fixture generation complete! ===")
    print(f"Files saved to: {FIXTURES_DIR}")


if __name__ == "__main__":
    main()

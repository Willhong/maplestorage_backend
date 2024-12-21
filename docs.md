Schemas
Character
{
ocid	
string
캐릭터 식별자

}
CharacterList
{
account_list	
[
메이플스토리 계정 목록

{
account_id	
string
메이플스토리 계정 식별자

character_list	
[
캐릭터 목록

{
ocid	
string
캐릭터 식별자

character_name	
string
캐릭터 명

world_name	
string
월드 명

character_class	
string
캐릭터 직업

character_level	
number($int64)
캐릭터 레벨

}
]
}
]
}
CharacterBasic
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_name	
string
캐릭터 명

world_name	
string
월드 명

character_gender	
string
캐릭터 성별

character_class	
string
캐릭터 직업

character_class_level	
string
캐릭터 전직 차수

character_level	
number($int64)
캐릭터 레벨

character_exp	
number($int64)
현재 레벨에서 보유한 경험치

character_exp_rate	
string
현재 레벨에서 경험치 퍼센트

character_guild_name	
string
캐릭터 소속 길드 명

character_image	
string
캐릭터 외형 이미지

조회된 캐릭터 외형 이미지 URL에 쿼리 파리미터를 사용하여 캐릭터 이미지의 동작이나 감정표현을 변경하실 수 있습니다
쿼리 파라미터는 API로 조회된 URL 뒤에 물음표(?)와 "Key=value" 쌍을 입력하여 조회합니다.
여러 개의 쿼리 파라미터를 전달하려면 파라미터 사이에 앰퍼샌드(&)을 추가하여 하나의 문자열로 입력합니다.
예시: https://open.api.nexon.com/static/maplestory/character/look/ABCDEFG?action=A00&emotion=E00&width=200&height=200
캐릭터 외형 이미지에 사용할 수 있는 쿼리 파라미터는 다음과 같습니다.
action: 액션 (A00 ~ A41)
A00: stand1 (default)
A01: stand2
A02: walk1
A03: walk2
A04: prone
A05: fly
A06: jump
A07: sit
A08: ladder
A09: rope
A10: heal
A11: alert
A12: proneStab
A13: swingO1
A14: swingO2
A15: swingO3
A16: swingOF
A17: swingP1
A18: swingP2
A19: swingPF
A20: swingT1
A21: swingT2
A22: swingT3
A23: swingTF
A24: stabO1
A25: stabO2
A26: stabOF
A27: stabT1
A28: stabT2
A29: stabTF
A30: shoot1
A31: shoot2
A32: shootF
A33: dead
A34: ghostwalk
A35: ghoststand
A36: ghostjump
A37: ghostproneStab
A38: ghostladder
A39: ghostrope
A40: ghostfly
A41: ghostsit
emotion: 감정표현 (E00 ~ E24)
E00: default (default)
E01: wink
E02: smile
E03: cry
E04: angry
E05: bewildered
E06: blink
E07: blaze
E08: bowing
E09: cheers
E10: chu
E11: dam
E12: despair
E13: glitter
E14: hit
E15: hot
E16: hum
E17: love
E18: oops
E19: pain
E20: troubled
E21: qBlue
E22: shine
E23: stunned
E24: vomit
wmotion: 무기 모션 (W00 ~ W04)
W00: 기본 모션 (default, 무기 타입에 따른 모션)
W01: 한손 모션
W02: 두손 모션
W03: 건 모션
W04: 무기 제외
width: 가로 길이 (배경 크기에 해당함, 96(default)~1000)
height: 세로 길이 (배경 크기에 해당함, 96(default)~1000)
x: 캐릭터의 가로 좌표 (좌표 범위 0 < x < width, 0은 왼쪽 시작점에 해당)
y: 캐릭터의 세로 좌표 (좌표 범위 0 < y < height, 0은 상단 시작점에 해당)
character_date_create	
string
example: 2023-12-21T00:00+09:00
캐릭터 생성일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

access_flag	
string
최근 7일간 접속 여부 (true 접속, false 미접속)

liberation_quest_clear_flag	
string
해방 퀘스트 완료 여부 (true 완료, false 미완료)

}
CharacterPopularity
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

popularity	
number($int64)
캐릭터 인기도

}
CharacterStat
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

final_stat	
[
현재 스탯 정보

{
stat_name	
string
example: 최소 스탯 공격력
스탯 명

stat_value	
string
example: 43.75
스탯 값

}
]
remain_ap	
number($int64)
잔여 AP

}
CharacterHyperStat
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

use_preset_no	
string
적용 중인 프리셋 번호

use_available_hyper_stat	
number($int64)
사용 가능한 최대 하이퍼스탯 포인트

hyper_stat_preset_1	
[
1번 프리셋 하이퍼 스탯 정보

{
stat_type	
string
스탯 종류

stat_point	
number($int64)
스탯 투자 포인트

stat_level	
number($int64)
스탯 레벨

stat_increase	
string
스탯 상승량

}
]
hyper_stat_preset_1_remain_point	
number($int64)
1번 프리셋 하이퍼 스탯 잔여 포인트

hyper_stat_preset_2	
[
2번 프리셋 하이퍼 스탯 정보

{
stat_type	
string
스탯 종류

stat_point	
number($int64)
스탯 투자 포인트

stat_level	
number($int64)
스탯 레벨

stat_increase	
string
스탯 상승량

}
]
hyper_stat_preset_2_remain_point	
number($int64)
2번 프리셋 하이퍼 스탯 잔여 포인트

hyper_stat_preset_3	
[
3번 프리셋 하이퍼 스탯 정보

{
stat_type	
string
스탯 종류

stat_point	
number($int64)
스탯 투자 포인트

stat_level	
number($int64)
스탯 레벨

stat_increase	
string
스탯 상승량

}
]
hyper_stat_preset_3_remain_point	
number($int64)
3번 프리셋 하이퍼 스탯 잔여 포인트

}
CharacterPropensity
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

charisma_level	
number($int64)
카리스마 레벨

sensibility_level	
number($int64)
감성 레벨

insight_level	
number($int64)
통찰력 레벨

willingness_level	
number($int64)
의지 레벨

handicraft_level	
number($int64)
손재주 레벨

charm_level	
number($int64)
매력 레벨

}
CharacterAbility
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

ability_grade	
string
어빌리티 등급

ability_info	
[
어빌리티 정보

{
ability_no	
string
어빌리티 번호

ability_grade	
string
어빌리티 등급

ability_value	
string
어빌리티 옵션 및 수치

}
]
remain_fame	
number($int64)
보유 명성치

preset_no	
number($int64)
적용 중인 어빌리티 프리셋 번호(number)

ability_preset_1	
{
description:	
어빌리티 1번 프리셋 전체 정보

ability_preset_grade	
string
어빌리티 1번 프리셋의 어빌리티 등급

ability_info	
[
어빌리티 1번 프리셋 정보

{
ability_no	
string
어빌리티 번호

ability_grade	
string
어빌리티 등급

ability_value	
string
어빌리티 옵션 및 수치

}
]
}
ability_preset_2	
{
description:	
어빌리티 2번 프리셋 전체 정보

ability_preset_grade	
string
어빌리티 2번 프리셋의 어빌리티 등급

ability_info	
[
어빌리티 2번 프리셋 정보

{
ability_no	
string
어빌리티 번호

ability_grade	
string
어빌리티 등급

ability_value	
string
어빌리티 옵션 및 수치

}
]
}
ability_preset_3	
{
description:	
어빌리티 3번 프리셋 전체 정보

ability_preset_grade	
string
어빌리티 3번 프리셋의 어빌리티 등급

ability_info	
[
어빌리티 3번 프리셋 정보

{
ability_no	
string
어빌리티 번호

ability_grade	
string
어빌리티 등급

ability_value	
string
어빌리티 옵션 및 수치

}
]
}
}
CharacterItemEquipment
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_gender	
string
캐릭터 성별

character_class	
string
캐릭터 직업

preset_no	
number($int64)
적용 중인 장비 프리셋 번호(number)

item_equipment	
[
장비 정보

{
item_equipment_part	
string
장비 부위 명

item_equipment_slot	
string
장비 슬롯 위치

item_name	
string
장비 명

item_icon	
string
장비 아이콘

item_description	
string
장비 설명

item_shape_name	
string
장비 외형

item_shape_icon	
string
장비 외형 아이콘

item_gender	
string
전용 성별

item_total_option	
{
description:	
장비 최종 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

damage	
string
데미지(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

}
item_base_option	
{
description:	
장비 기본 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

base_equipment_level	
number($int64)
기본 착용 레벨

}
potential_option_flag	
string
잠재능력 봉인 여부 (true 봉인, false 봉인 없음)

additional_potential_option_flag	
string
에디셔널 잠재능력 봉인 여부 (true 봉인, false 봉인 없음)

potential_option_grade	
string
잠재능력 등급

additional_potential_option_grade	
string
에디셔널 잠재능력 등급

potential_option_1	
string
잠재능력 첫 번째 옵션

potential_option_2	
string
잠재능력 두 번째 옵션

potential_option_3	
string
잠재능력 세 번째 옵션

additional_potential_option_1	
string
에디셔널 잠재능력 첫 번째 옵션

additional_potential_option_2	
string
에디셔널 잠재능력 두 번째 옵션

additional_potential_option_3	
string
에디셔널 잠재능력 세 번째 옵션

equipment_level_increase	
number($int64)
착용 레벨 증가

item_exceptional_option	
{
description:	
장비 특별 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

exceptional_upgrade	
number($int64)
익셉셔널 강화 적용 횟수

}
item_add_option	
{
description:	
장비 추가 옵션

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

damage	
string
데미지(%)

all_stat	
string
올스탯(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

}
growth_exp	
number($int64)
성장 경험치

growth_level	
number($int64)
성장 레벨

scroll_upgrade	
string
업그레이드 횟수

cuttable_count	
string
가위 사용 가능 횟수 (교환 불가 장비, 가위 횟수가 없는 교환 가능 장비는 255)

golden_hammer_flag	
string
황금 망치 재련 적용 (1:적용, 이외 미 적용)

scroll_resilience_count	
string
복구 가능 횟수

scroll_upgradable_count	
string
업그레이드 가능 횟수

soul_name	
string
소울 명

soul_option	
string
소울 옵션

item_etc_option	
{
description:	
장비 기타 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
starforce	
string
강화 단계

starforce_scroll_flag	
string
놀라운 장비 강화 주문서 사용 여부 (0:미사용, 1:사용)

item_starforce_option	
{
description:	
장비 스타포스 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
special_ring_level	
number($int64)
특수 반지 레벨

date_expire	
string
example: 2023-12-21T17:28+09:00
장비 유효 기간(KST)

}
]
item_equipment_preset_1	
[
1번 프리셋 장비 정보

{
item_equipment_part	
string
장비 부위 명

equipment_slot	
string
장비 슬롯 위치

item_name	
string
장비 명

item_icon	
string
장비 아이콘

item_description	
string
장비 설명

item_shape_name	
string
장비 외형

item_shape_icon	
string
장비 외형 아이콘

item_gender	
string
전용 성별

item_total_option	
{
description:	
장비 최종 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

damage	
string
데미지(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

}
item_base_option	
{
description:	
장비 기본 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

base_equipment_level	
number($int64)
기본 착용 레벨

}
potential_option_grade	
string
잠재능력 등급

additional_potential_option_grade	
string
에디셔널 잠재능력 등급

potential_option_1	
string
잠재능력 첫 번째 옵션

potential_option_2	
string
잠재능력 두 번째 옵션

potential_option_3	
string
잠재능력 세 번째 옵션

additional_potential_option_1	
string
에디셔널 잠재능력 첫 번째 옵션

additional_potential_option_2	
string
에디셔널 잠재능력 두 번째 옵션

additional_potential_option_3	
string
에디셔널 잠재능력 세 번째 옵션

equipment_level_increase	
number($int64)
착용 레벨 증가

item_exceptional_option	
{
description:	
장비 특별 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

exceptional_upgrade	
number($int64)
익셉셔널 강화 적용 횟수

}
item_add_option	
{
description:	
장비 추가 옵션

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

damage	
string
데미지(%)

all_stat	
string
올스탯(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

}
growth_exp	
number($int64)
성장 경험치

growth_level	
number($int64)
성장 레벨

scroll_upgrade	
string
업그레이드 횟수

cuttable_count	
string
가위 사용 가능 횟수 (교환 불가 장비, 가위 횟수가 없는 교환 가능 장비는 255)

golden_hammer_flag	
string
황금 망치 재련 적용 (1:적용, 이외 미 적용)

scroll_resilience_count	
string
복구 가능 횟수

scroll_upgradable_count	
string
업그레이드 가능 횟수

soul_name	
string
소울 명

soul_option	
string
소울 옵션

item_etc_option	
{
description:	
장비 기타 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
starforce	
string
강화 단계

starforce_scroll_flag	
string
놀라운 장비 강화 주문서 사용 여부 (0:미사용, 1:사용)

item_starforce_option	
{
description:	
장비 스타포스 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
special_ring_level	
number($int64)
특수 반지 레벨

date_expire	
string
example: 2023-12-21T17:28+09:00
장비 유효 기간(KST)

}
]
item_equipment_preset_2	
[
2번 프리셋 장비 정보

{
item_equipment_part	
string
장비 부위 명

equipment_slot	
string
장비 슬롯 위치

item_name	
string
장비 명

item_icon	
string
장비 아이콘

item_description	
string
장비 설명

item_shape_name	
string
장비 외형

item_shape_icon	
string
장비 외형 아이콘

item_gender	
string
전용 성별

item_total_option	
{
description:	
장비 최종 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

damage	
string
데미지(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

}
item_base_option	
{
description:	
장비 기본 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

base_equipment_level	
number($int64)
기본 착용 레벨

}
potential_option_grade	
string
잠재능력 등급

additional_potential_option_grade	
string
에디셔널 잠재능력 등급

potential_option_1	
string
잠재능력 첫 번째 옵션

potential_option_2	
string
잠재능력 두 번째 옵션

potential_option_3	
string
잠재능력 세 번째 옵션

additional_potential_option_1	
string
에디셔널 잠재능력 첫 번째 옵션

additional_potential_option_2	
string
에디셔널 잠재능력 두 번째 옵션

additional_potential_option_3	
string
에디셔널 잠재능력 세 번째 옵션

equipment_level_increase	
number($int64)
착용 레벨 증가

item_exceptional_option	
{
description:	
장비 특별 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

exceptional_upgrade	
number($int64)
익셉셔널 강화 적용 횟수

}
item_add_option	
{
description:	
장비 추가 옵션

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

damage	
string
데미지(%)

all_stat	
string
올스탯(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

}
growth_exp	
number($int64)
성장 경험치

growth_level	
number($int64)
성장 레벨

scroll_upgrade	
string
업그레이드 횟수

cuttable_count	
string
가위 사용 가능 횟수 (교환 불가 장비, 가위 횟수가 없는 교환 가능 장비는 255)

golden_hammer_flag	
string
황금 망치 재련 적용 (1:적용, 이외 미 적용)

scroll_resilience_count	
string
복구 가능 횟수

scroll_upgradable_count	
string
업그레이드 가능 횟수

soul_name	
string
소울 명

soul_option	
string
소울 옵션

item_etc_option	
{
description:	
장비 기타 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
starforce	
string
강화 단계

starforce_scroll_flag	
string
놀라운 장비 강화 주문서 사용 여부 (0:미사용, 1:사용)

item_starforce_option	
{
description:	
장비 스타포스 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
special_ring_level	
number($int64)
특수 반지 레벨

date_expire	
string
example: 2023-12-21T17:28+09:00
장비 유효 기간(KST)

}
]
item_equipment_preset_3	
[
3번 프리셋 장비 정보

{
item_equipment_part	
string
장비 부위 명

equipment_slot	
string
장비 슬롯 위치

item_name	
string
장비 명

item_icon	
string
장비 아이콘

item_description	
string
장비 설명

item_shape_name	
string
장비 외형

item_shape_icon	
string
장비 외형 아이콘

item_gender	
string
전용 성별

item_total_option	
{
description:	
장비 최종 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

damage	
string
데미지(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

}
item_base_option	
{
description:	
장비 기본 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

base_equipment_level	
number($int64)
기본 착용 레벨

}
potential_option_grade	
string
잠재능력 등급

additional_potential_option_grade	
string
에디셔널 잠재능력 등급

potential_option_1	
string
잠재능력 첫 번째 옵션

potential_option_2	
string
잠재능력 두 번째 옵션

potential_option_3	
string
잠재능력 세 번째 옵션

additional_potential_option_1	
string
에디셔널 잠재능력 첫 번째 옵션

additional_potential_option_2	
string
에디셔널 잠재능력 두 번째 옵션

additional_potential_option_3	
string
에디셔널 잠재능력 세 번째 옵션

equipment_level_increase	
number($int64)
착용 레벨 증가

item_exceptional_option	
{
description:	
장비 특별 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

exceptional_upgrade	
number($int64)
익셉셔널 강화 적용 횟수

}
item_add_option	
{
description:	
장비 추가 옵션

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

damage	
string
데미지(%)

all_stat	
string
올스탯(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

}
growth_exp	
number($int64)
성장 경험치

growth_level	
number($int64)
성장 레벨

scroll_upgrade	
string
업그레이드 횟수

cuttable_count	
string
가위 사용 가능 횟수 (교환 불가 장비, 가위 횟수가 없는 교환 가능 장비는 255)

golden_hammer_flag	
string
황금 망치 재련 적용 (1:적용, 이외 미 적용)

scroll_resilience_count	
string
복구 가능 횟수

scroll_upgradable_count	
string
업그레이드 가능 횟수

soul_name	
string
소울 명

soul_option	
string
소울 옵션

item_etc_option	
{
description:	
장비 기타 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
starforce	
string
강화 단계

starforce_scroll_flag	
string
놀라운 장비 강화 주문서 사용 여부 (0:미사용, 1:사용)

item_starforce_option	
{
description:	
장비 스타포스 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
special_ring_level	
number($int64)
특수 반지 레벨

date_expire	
string
example: 2023-12-21T17:28+09:00
장비 유효 기간(KST)

}
]
title	
{
description:	
칭호 정보

title_name	
string
칭호 장비 명

title_icon	
string
칭호 아이콘

title_description	
string
칭호 설명

date_expire	
string
example: 2023-12-21T17:28+09:00
칭호 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:28+09:00
칭호 옵션 유효 기간 (expired:만료, null:무제한) (KST)

}
dragon_equipment	
[
에반 드래곤 장비 정보 (에반인 경우 응답)

{
item_equipment_part	
string
장비 부위 명

equipment_slot	
string
장비 슬롯 위치

item_name	
string
장비 명

item_icon	
string
장비 아이콘

item_description	
string
장비 설명

item_shape_name	
string
장비 외형

item_shape_icon	
string
장비 외형 아이콘

item_gender	
string
전용 성별

item_total_option	
{
description:	
장비 최종 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

damage	
string
데미지(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

}
item_base_option	
{
description:	
장비 기본 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

base_equipment_level	
number($int64)
기본 착용 레벨

}
equipment_level_increase	
number($int64)
착용 레벨 증가

item_exceptional_option	
{
description:	
장비 특별 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

}
item_add_option	
{
description:	
장비 추가 옵션

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

damage	
string
데미지(%)

all_stat	
string
올스탯(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

}
growth_exp	
number($int64)
성장 경험치

growth_level	
number($int64)
성장 레벨

scroll_upgrade	
string
업그레이드 횟수

cuttable_count	
string
가위 사용 가능 횟수 (교환 불가 장비, 가위 횟수가 없는 교환 가능 장비는 255)

golden_hammer_flag	
string
황금 망치 재련 적용 (1:적용, 이외 미 적용)

scroll_resilience_count	
string
복구 가능 횟수

scroll_upgradable_count	
string
업그레이드 가능 횟수

soul_name	
string
소울 명

soul_option	
string
소울 옵션

item_etc_option	
{
description:	
장비 기타 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
starforce	
string
강화 단계

starforce_scroll_flag	
string
놀라운 장비 강화 주문서 사용 여부 (0:미사용, 1:사용)

item_starforce_option	
{
description:	
장비 스타포스 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
special_ring_level	
number($int64)
특수 반지 레벨

date_expire	
string
example: 2023-12-21T17:28+09:00
장비 유효 기간(KST)

}
]
mechanic_equipment	
[
메카닉 장비 정보 (메카닉인 경우 응답)

{
item_equipment_part	
string
장비 부위 명

equipment_slot	
string
장비 슬롯 위치

item_name	
string
장비 명

item_icon	
string
장비 아이콘

item_description	
string
장비 설명

item_shape_name	
string
장비 외형

item_shape_icon	
string
장비 외형 아이콘

item_gender	
string
전용 성별

item_total_option	
{
description:	
장비 최종 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

damage	
string
데미지(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

}
item_base_option	
{
description:	
장비 기본 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

ignore_monster_armor	
string
몬스터 방어율 무시(%)

all_stat	
string
올스탯(%)

max_hp_rate	
string
최대 HP(%)

max_mp_rate	
string
최대 MP(%)

base_equipment_level	
number($int64)
기본 착용 레벨

}
equipment_level_increase	
number($int64)
착용 레벨 증가

item_exceptional_option	
{
description:	
장비 특별 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

}
item_add_option	
{
description:	
장비 추가 옵션

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

boss_damage	
string
보스 공격 시 데미지 증가(%)

damage	
string
데미지(%)

all_stat	
string
올스탯(%)

equipment_level_decrease	
number($int64)
착용 레벨 감소

}
growth_exp	
number($int64)
성장 경험치

growth_level	
number($int64)
성장 레벨

scroll_upgrade	
string
업그레이드 횟수

cuttable_count	
string
가위 사용 가능 횟수 (교환 불가 장비, 가위 횟수가 없는 교환 가능 장비는 255)

golden_hammer_flag	
string
황금 망치 재련 적용 (1:적용, 이외 미 적용)

scroll_resilience_count	
string
복구 가능 횟수

scroll_upgradable_count	
string
업그레이드 가능 횟수

soul_name	
string
소울 명

soul_option	
string
소울 옵션

item_etc_option	
{
description:	
장비 기타 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
starforce	
string
강화 단계

starforce_scroll_flag	
string
놀라운 장비 강화 주문서 사용 여부 (0:미사용, 1:사용)

item_starforce_option	
{
description:	
장비 스타포스 옵션 정보

str	
string
STR

dex	
string
DEX

int	
string
INT

luk	
string
LUK

max_hp	
string
최대 HP

max_mp	
string
최대 MP

attack_power	
string
공격력

magic_power	
string
마력

armor	
string
방어력

speed	
string
이동속도

jump	
string
점프력

}
special_ring_level	
number($int64)
특수 반지 레벨

date_expire	
string
example: 2023-12-21T17:28+09:00
장비 유효 기간(KST)

}
]
}
CharacterCashItemEquipment
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_gender	
string
캐릭터 성별

character_class	
string
캐릭터 직업

character_look_mode	
string
캐릭터 외형 모드(0:일반 모드, 1:제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드)

preset_no	
number($int64)
적용 중인 캐시 장비 프리셋 번호

cash_item_equipment_base	
[
장착 중인 캐시 장비

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
cash_item_equipment_preset_1	
[
1번 코디 프리셋

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
cash_item_equipment_preset_2	
[
2번 코디 프리셋

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
cash_item_equipment_preset_3	
[
3번 코디 프리셋

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
additional_cash_item_equipment_base	
[
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드에서 장착 중인 캐시 장비

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
additional_cash_item_equipment_preset_1	
[
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드의 1번 코디 프리셋

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
additional_cash_item_equipment_preset_2	
[
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드의 2번 코디 프리셋

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
아이템 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
additional_cash_item_equipment_preset_3	
[
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드의 3번 코디 프리셋

{
cash_item_equipment_part	
string
캐시 장비 부위 명

cash_item_equipment_slot	
string
캐시 장비 슬롯 위치

cash_item_name	
string
캐시 장비 명

cash_item_icon	
string
캐시 장비 아이콘

cash_item_description	
string
캐시 장비 설명

cash_item_option	
[
캐시 장비 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
캐시 장비 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
캐시 장비 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
캐시 장비 라벨 정보

cash_item_coloring_prism	
{
description:	
캐시 장비 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
item_gender	
string
아이템 장착 가능 성별

}
]
}
CharacterSymbolEquipment
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

symbol	
[
심볼 정보

{
symbol_name	
string
심볼 명

symbol_icon	
string
심볼 아이콘

symbol_description	
string
심볼 설명

symbol_force	
string
심볼로 인한 증가 수치

symbol_level	
number($int64)
심볼 레벨

symbol_str	
string
심볼로 증가한 힘

symbol_dex	
string
심볼로 증가한 민첩

symbol_int	
string
심볼로 증가한 지력

symbol_luk	
string
심볼로 증가한 운

symbol_hp	
string
심볼로 증가한 체력

symbol_drop_rate	
string
심볼로 증가한 아이템 드롭률

symbol_meso_rate	
string
심볼로 증가한 메소 획득량

symbol_exp_rate	
string
심볼로 증가한 경험치 획득량

symbol_growth_count	
number($int64)
현재 보유 성장치

symbol_require_growth_count	
number($int64)
성장 시 필요한 성장치

}
]
}
CharacterSetEffect
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

set_effect	
[
세트 효과 정보

{
set_name	
string
세트 효과 명

total_set_count	
number($int64)
세트 개수 (럭키 아이템 포함)

set_effect_info	
[
적용 중인 세트 효과 정보

{
set_count	
number($int64)
세트 효과 레벨 (장비 수)

set_option	
string
세트 효과

}
]
set_effect_full_info	
[
모든 세트 효과 정보

{
set_count	
number($int64)
세트 효과 레벨 (장비 수)

set_option	
string
세트 효과

}
]
}
]
}
CharacterBeautyEquipment
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST)

character_gender	
string
캐릭터 성별

character_class	
string
캐릭터 직업

character_hair	
{
description:	
캐릭터 헤어 정보
(제로인 경우 알파, 엔젤릭버스터인 경우 일반 모드)

hair_name	
string
헤어 명

base_color	
string
헤어 베이스 컬러

mix_color	
string
헤어 믹스 컬러

mix_rate	
string
헤어 믹스 컬러의 염색 비율

}
character_face	
{
description:	
캐릭터 성형 정보
(제로인 경우 알파, 엔젤릭버스터인 경우 일반 모드)

face_name	
string
성형 명

base_color	
string
성형 베이스 컬러

mix_color	
string
성형 믹스 컬러

mix_rate	
string
성형 믹스 컬러의 염색 비율

}
character_skin	
{
description:	
캐릭터 피부 정보
(제로인 경우 알파, 엔젤릭버스터인 경우 일반 모드)

skin_name	
string
피부 명

color_style	
string
색상 계열

hue	
number($int64)
피부 색조

saturation	
number($int64)
피부 채도

brightness	
number($int64)
피부 명도

}
additional_character_hair	
{
description:	
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드에 적용 중인 헤어 정보

hair_name	
string
헤어 명

base_color	
string
헤어 베이스 컬러

mix_color	
string
헤어 믹스 컬러

mix_rate	
string
헤어 믹스 컬러의 염색 비율

}
additional_character_face	
{
description:	
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드에 적용 중인 성형 정보

face_name	
string
성형 명

base_color	
string
성형 베이스 컬러

mix_color	
string
성형 믹스 컬러

mix_rate	
string
성형 믹스 컬러의 염색 비율

}
additional_character_skin	
{
description:	
제로인 경우 베타, 엔젤릭버스터인 경우 드레스 업 모드에 적용 중인 피부 정보

skin_name	
string
피부 명

color_style	
string
색상 계열

hue	
number($int64)
피부 색조

saturation	
number($int64)
피부 채도

brightness	
number($int64)
피부 명도

}
}
CharacterAndroidEquipment
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

android_name	
string
안드로이드 명

android_nickname	
string
안드로이드 닉네임

android_icon	
string
안드로이드 아이콘

android_description	
string
안드로이드 아이템 설명

android_hair	
{
description:	
안드로이드 헤어 정보

hair_name	
string
안드로이드 헤어 명

base_color	
string
안드로이드 헤어 베이스 컬러

mix_color	
string
안드로이드 헤어 믹스 컬러

mix_rate	
string
안드로이드 헤어 믹스 컬러의 염색 비율

}
android_face	
{
description:	
안드로이드 성형 정보

face_name	
string
안드로이드 성형 명

base_color	
string
안드로이드 성형 베이스 컬러

mix_color	
string
안드로이드 성형 믹스 컬러

mix_rate	
string
안드로이드 성형 믹스 컬러의 염색 비율

}
android_skin	
{
description:	
안드로이드 피부 정보

skin_name	
string
피부 명

color_style	
string
색상 계열

hue	
number($int64)
피부 색조

saturation	
number($int64)
피부 채도

brightness	
number($int64)
피부 명도

}
android_cash_item_equipment	
[
안드로이드 캐시 아이템 장착 정보

{
cash_item_equipment_part	
string
안드로이드 캐시 아이템 부위 명

cash_item_equipment_slot	
string
안드로이드 캐시 아이템 슬롯 위치

cash_item_name	
string
안드로이드 캐시 아이템 명

cash_item_icon	
string
안드로이드 캐시 아이템 아이콘

cash_item_description	
string
안드로이드 캐시 아이템 설명

cash_item_option	
[
안드로이드 캐시 아이템 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
date_expire	
string
example: 2023-12-21T17:28+09:00
안드로이드 캐시 아이템 유효 기간 (KST)

date_option_expire	
string
example: 2023-12-21T17:00+09:00
안드로이드 캐시 아이템 옵션 유효 기간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

cash_item_label	
string
안드로이드 캐시 아이템 라벨 정보 (스페셜라벨, 레드라벨, 블랙라벨, 마스터라벨)

cash_item_coloring_prism	
{
description:	
안드로이드 캐시 아이템 컬러링프리즘 정보

color_range	
string
컬러링프리즘 색상 범위

hue	
number($int64)
컬러링프리즘 색조

saturation	
number($int64)
컬러링프리즘 채도

value	
number($int64)
컬러링프리즘 명도

}
android_item_gender	
string
아이템 장착 가능 성별

}
]
android_ear_sensor_clip_flag	
string
안드로이드 이어센서 클립 적용 여부

android_gender	
string
안드로이드 성별

android_grade	
string
안드로이드 등급

android_non_humanoid_flag	
string
비인간형 안드로이드 여부

android_shop_usable_flag	
string
잡화상점 기능 이용 가능 여부

preset_no	
number($int64)
적용 중인 장비 프리셋 번호(number)

android_preset_1	
{
description:	
1번 프리셋 안드로이드 정보

android_name	
string
안드로이드 명

android_nickname	
string
안드로이드 닉네임

android_icon	
string
안드로이드 아이콘

android_description	
string
안드로이드 아이템 설명

android_gender	
string
안드로이드 성별

android_grade	
string
안드로이드 등급

android_skin	
{
description:	
안드로이드 피부 정보

skin_name	
string
피부 명

color_style	
string
색상 계열

hue	
number($int64)
피부 색조

saturation	
number($int64)
피부 채도

brightness	
number($int64)
피부 명도

}
android_hair	
{
description:	
안드로이드 헤어 정보

hair_name	
string
안드로이드 헤어 명

base_color	
string
안드로이드 헤어 베이스 컬러

mix_color	
string
안드로이드 헤어 믹스 컬러

mix_rate	
string
안드로이드 헤어 믹스 컬러의 염색 비율

}
android_face	
{
description:	
안드로이드 성형 정보

face_name	
string
안드로이드 성형 명

base_color	
string
안드로이드 성형 베이스 컬러

mix_color	
string
안드로이드 성형 믹스 컬러

mix_rate	
string
안드로이드 성형 믹스 컬러의 염색 비율

}
android_ear_sensor_clip_flag	
string
안드로이드 이어센서 클립 적용 여부

android_non_humanoid_flag	
string
비인간형 안드로이드 여부

android_shop_usable_flag	
string
잡화상점 기능 이용 가능 여부

}
android_preset_2	
{
description:	
2번 프리셋 안드로이드 정보

android_name	
string
안드로이드 명

android_nickname	
string
안드로이드 닉네임

android_icon	
string
안드로이드 아이콘

android_description	
string
안드로이드 아이템 설명

android_gender	
string
안드로이드 성별

android_grade	
string
안드로이드 등급

android_skin	
{
description:	
안드로이드 피부 정보

skin_name	
string
피부 명

color_style	
string
색상 계열

hue	
number($int64)
피부 색조

saturation	
number($int64)
피부 채도

brightness	
number($int64)
피부 명도

}
android_hair	
{
description:	
안드로이드 헤어 정보

hair_name	
string
안드로이드 헤어 명

base_color	
string
안드로이드 헤어 베이스 컬러

mix_color	
string
안드로이드 헤어 믹스 컬러

mix_rate	
string
안드로이드 헤어 믹스 컬러의 염색 비율

}
android_face	
{
description:	
안드로이드 성형 정보

face_name	
string
안드로이드 성형 명

base_color	
string
안드로이드 성형 베이스 컬러

mix_color	
string
안드로이드 성형 믹스 컬러

mix_rate	
string
안드로이드 성형 믹스 컬러의 염색 비율

}
android_ear_sensor_clip_flag	
string
안드로이드 이어센서 클립 적용 여부

android_non_humanoid_flag	
string
비인간형 안드로이드 여부

android_shop_usable_flag	
string
잡화상점 기능 이용 가능 여부

}
android_preset_3	
{
description:	
3번 프리셋 안드로이드 정보

android_name	
string
안드로이드 명

android_nickname	
string
안드로이드 닉네임

android_icon	
string
안드로이드 아이콘

android_description	
string
안드로이드 아이템 설명

android_gender	
string
안드로이드 성별

android_grade	
string
안드로이드 등급

android_skin	
{
description:	
안드로이드 피부 정보

skin_name	
string
피부 명

color_style	
string
색상 계열

hue	
number($int64)
피부 색조

saturation	
number($int64)
피부 채도

brightness	
number($int64)
피부 명도

}
android_hair	
{
description:	
안드로이드 헤어 정보

hair_name	
string
안드로이드 헤어 명

base_color	
string
안드로이드 헤어 베이스 컬러

mix_color	
string
안드로이드 헤어 믹스 컬러

mix_rate	
string
안드로이드 헤어 믹스 컬러의 염색 비율

}
android_face	
{
description:	
안드로이드 성형 정보

face_name	
string
안드로이드 성형 명

base_color	
string
안드로이드 성형 베이스 컬러

mix_color	
string
안드로이드 성형 믹스 컬러

mix_rate	
string
안드로이드 성형 믹스 컬러의 염색 비율

}
android_ear_sensor_clip_flag	
string
안드로이드 이어센서 클립 적용 여부

android_non_humanoid_flag	
string
비인간형 안드로이드 여부

android_shop_usable_flag	
string
잡화상점 기능 이용 가능 여부

}
}
CharacterPetEquipment
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

pet_1_name	
string
펫1 명

pet_1_nickname	
string
펫1 닉네임

pet_1_icon	
string
펫1 아이콘

pet_1_description	
string
펫1 설명

pet_1_equipment	
{
description:	
펫1 장착 정보

item_name	
string
아이템 명

item_icon	
string
아이템 아이콘

item_description	
string
아이템 설명

item_option	
[
아이템 표기상 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
scroll_upgrade	
number($int64)
업그레이드 횟수

scroll_upgradable	
number($int64)
업그레이드 가능 횟수

item_shape	
string
아이템 외형

item_shape_icon	
string
아이템 외형 아이콘

}
pet_1_auto_skill	
{
description:	
펫1 펫 버프 자동스킬 정보

skill_1	
string
첫 번째 슬롯에 등록된 자동 스킬

skill_1_icon	
string
첫 번째 슬롯에 등록된 자동 스킬 아이콘

skill_2	
string
두 번째 슬롯에 등록된 자동 스킬

skill_2_icon	
string
두 번째 슬롯에 등록된 자동 스킬 아이콘

}
pet_1_pet_type	
string
펫1 원더 펫 종류

pet_1_skill	
[
펫1 펫 보유 스킬

string
]
pet_1_date_expire	
string
example: 2023-12-21T17:00+09:00
펫1 마법의 시간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

pet_1_appearance	
string
펫1 외형

pet_1_appearance_icon	
string
펫1 외형 아이콘

pet_2_name	
string
펫2 명

pet_2_nickname	
string
펫2 닉네임

pet_2_icon	
string
펫2 아이콘

pet_2_description	
string
펫2 설명

pet_2_equipment	
{
description:	
펫2 장착 정보

item_name	
string
아이템 명

item_icon	
string
아이템 아이콘

item_description	
string
아이템 설명

item_option	
[
아이템 표기상 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
scroll_upgrade	
number($int64)
업그레이드 횟수

scroll_upgradable	
number($int64)
업그레이드 가능 횟수

item_shape	
string
아이템 외형

item_shape_icon	
string
아이템 외형 아이콘

}
pet_2_auto_skill	
{
description:	
펫2 펫 버프 자동 스킬 정보

skill_1	
string
첫 번째 슬롯에 등록된 자동 스킬

skill_1_icon	
string
첫 번째 슬롯에 등록된 자동 스킬 아이콘

skill_2	
string
두 번째 슬롯에 등록된 자동 스킬

skill_2_icon	
string
두 번째 슬롯에 등록된 자동 스킬 아이콘

}
pet_2_pet_type	
string
펫2 원더 펫 종류

pet_2_skill	
[
펫2 펫 보유 스킬

string
]
pet_2_date_expire	
string
example: 2023-12-21T17:00+09:00
펫2 마법의 시간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

pet_2_appearance	
string
펫2 외형

pet_2_appearance_icon	
string
펫2 외형 아이콘

pet_3_name	
string
펫3 명

pet_3_nickname	
string
펫3 닉네임

pet_3_icon	
string
펫3 아이콘

pet_3_description	
string
펫3 설명

pet_3_equipment	
{
description:	
펫3 장착 정보

item_name	
string
아이템 명

item_icon	
string
아이템 아이콘

item_description	
string
아이템 설명

item_option	
[
아이템 표기상 옵션

{
option_type	
string
옵션 타입

option_value	
string
옵션 값

}
]
scroll_upgrade	
number($int64)
업그레이드 횟수

scroll_upgradable	
number($int64)
업그레이드 가능 횟수

item_shape	
string
아이템 외형

item_shape_icon	
string
아이템 외형 아이콘

}
pet_3_auto_skill	
{
description:	
펫3 펫 버프 자동 스킬 정보

skill_1	
string
첫 번째 슬롯에 등록된 자동 스킬

skill_1_icon	
string
첫 번째 슬롯에 등록된 자동 스킬 아이콘

skill_2	
string
두 번째 슬롯에 등록된 자동 스킬

skill_2_icon	
string
두 번째 슬롯에 등록된 자동 스킬 아이콘

}
pet_3_pet_type	
string
펫3 원더 펫 종류

pet_3_skill	
[
펫3 펫 보유 스킬

string
]
pet_3_date_expire	
string
example: 2023-12-21T17:00+09:00
펫3 마법의 시간 (KST, 시간 단위 데이터로 분은 일괄 0으로 표기)

pet_3_appearance	
string
펫3 외형

pet_3_appearance_icon	
string
펫3 외형 아이콘

}
CharacterSkill
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

character_skill_grade	
string
스킬 전직 차수

character_skill	
[
스킬 정보

{
skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 레벨 별 효과 설명

skill_effect_next	
string
다음 스킬 레벨 효과 설명

skill_icon	
string
스킬 아이콘

}
]
}
CharacterLinkSkill
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

character_link_skill	
{
description:	
링크 스킬 정보

skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_effect_next	
string
다음 레벨의 스킬 효과

skill_icon	
string
스킬 아이콘

}
character_link_skill_preset_1	
[
링크 스킬 1번 프리셋 정보

{
skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
]
character_link_skill_preset_2	
[
링크 스킬 2번 프리셋 정보

{
skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
]
character_link_skill_preset_3	
[
링크 스킬 3번 프리셋 정보

{
skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
]
character_owned_link_skill	
{
description:	
내 링크 스킬 정보

skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
character_owned_link_skill_preset_1	
{
description:	
내 링크 스킬 1번 프리셋 정보

skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
character_owned_link_skill_preset_2	
{
description:	
내 링크 스킬 2번 프리셋 정보

skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
character_owned_link_skill_preset_3	
{
description:	
내 링크 스킬 3번 프리셋 정보

skill_name	
string
스킬 명

skill_description	
string
스킬 설명

skill_level	
number($int64)
스킬 레벨

skill_effect	
string
스킬 효과

skill_icon	
string
스킬 아이콘

}
}
CharacterVMatrix
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

character_v_core_equipment	
[
V코어 정보

{
slot_id	
string
슬롯 인덱스

slot_level	
number($int64)
슬롯 레벨

v_core_name	
string
코어 명

v_core_type	
string
코어 타입

v_core_level	
number($int64)
코어 레벨

v_core_skill_1	
string
코어에 해당하는 스킬 명

v_core_skill_2	
string
(강화 코어인 경우) 코어에 해당하는 두 번째 스킬 명

v_core_skill_3	
string
(강화 코어인 경우) 코어에 해당하는 세 번째 스킬 명

}
]
character_v_matrix_remain_slot_upgrade_point	
number($int64)
캐릭터 잔여 매트릭스 강화 포인트

}
CharacterHexaMatrix
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_hexa_core_equipment	
[
HEXA 코어 정보

{
hexa_core_name	
string
코어 명

hexa_core_level	
number($int64)
코어 레벨

hexa_core_type	
string
코어 타입

linked_skill	
[
연결된 스킬

{
hexa_skill_id	
string
HEXA 스킬 명

}
]
}
]
}
CharacterHexaMatrixStat
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

character_hexa_stat_core	
[
HEXA 스탯 I 코어 정보

{
slot_id	
string
슬롯 인덱스

main_stat_name	
string
메인 스탯 명

sub_stat_name_1	
string
첫 번째 서브 명

sub_stat_name_2	
string
두 번째 서브 명

main_stat_level	
number($int64)
메인 스탯 레벨

sub_stat_level_1	
number($int64)
첫 번째 서브 레벨

sub_stat_level_2	
number($int64)
두 번째 서브 레벨

stat_grade	
number($int64)
스탯 코어 등급

}
]
character_hexa_stat_core_2	
[
HEXA 스탯 II 코어 정보

{
slot_id	
string
슬롯 인덱스

main_stat_name	
string
메인 스탯 명

sub_stat_name_1	
string
첫 번째 서브 명

sub_stat_name_2	
string
두 번째 서브 명

main_stat_level	
number($int64)
메인 스탯 레벨

sub_stat_level_1	
number($int64)
첫 번째 서브 레벨

sub_stat_level_2	
number($int64)
두 번째 서브 레벨

stat_grade	
number($int64)
스탯 코어 등급

}
]
preset_hexa_stat_core	
[
프리셋 HEXA 스탯 I 코어 정보

{
slot_id	
string
슬롯 인덱스

main_stat_name	
string
메인 스탯 명

sub_stat_name_1	
string
첫 번째 서브 명

sub_stat_name_2	
string
두 번째 서브 명

main_stat_level	
number($int64)
메인 스탯 레벨

sub_stat_level_1	
number($int64)
첫 번째 서브 레벨

sub_stat_level_2	
number($int64)
두 번째 서브 레벨

stat_grade	
number($int64)
스탯 코어 등급

}
]
preset_hexa_stat_core_2	
[
프리셋 HEXA 스탯 II 코어 정보

{
slot_id	
string
슬롯 인덱스

main_stat_name	
string
메인 스탯 명

sub_stat_name_1	
string
첫 번째 서브 명

sub_stat_name_2	
string
두 번째 서브 명

main_stat_level	
number($int64)
메인 스탯 레벨

sub_stat_level_1	
number($int64)
첫 번째 서브 레벨

sub_stat_level_2	
number($int64)
두 번째 서브 레벨

stat_grade	
number($int64)
스탯 코어 등급

}
]
}
CharacterDojang
{
date	
string
example: 2023-12-21T00:00+09:00
조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

character_class	
string
캐릭터 직업

world_name	
string
월드 명

dojang_best_floor	
number($int64)
무릉도장 최고 기록 층수

date_dojang_record	
string
example: 2023-12-21T00:00+09:00
무릉도장 최고 기록 달성 일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)

dojang_best_time	
number($int64)
무릉도장 최고 층수 클리어에 걸린 시간 (초)

}
ErrorMessage
{
error	
{
name	
string
에러 명

message	
string
에러 설명

}
}
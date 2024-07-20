# schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class CharacterBasicSchema(BaseModel):
    date: datetime = Field(..., description="조회 기준일 (KST)")
    character_name: str = Field(..., description="캐릭터 명")
    world_name: str = Field(..., description="월드 명")
    character_gender: str = Field(..., description="캐릭터 성별")
    character_class: str = Field(..., description="캐릭터 직업")
    character_class_level: str = Field(..., description="캐릭터 전직 차수")
    character_level: int = Field(..., description="캐릭터 레벨")
    character_exp: int = Field(..., description="현재 레벨에서 보유한 경험치")
    character_exp_rate: str = Field(..., description="현재 레벨에서 경험치 퍼센트")
    character_guild_name: Optional[str] = Field(
        None, description="캐릭터 소속 길드 명")
    character_image: str = Field(..., description="캐릭터 외형 이미지")
    character_date_create: Optional[datetime] = Field(
        None, description="캐릭터 생성일 (KST)")
    access_flag: bool = Field(..., description="최근 7일간 접속 여부")
    liberation_quest_clear_flag: bool = Field(..., description="해방 퀘스트 완료 여부")

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M%z")
        }


class CharacterPopularitySchema(BaseModel):
    date: Optional[datetime] = Field(
        None, description="조회 기준일 (KST, 일 단위 데이터로 시, 분은 일괄 0으로 표기)")
    popularity: int

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime("%Y-%m-%dT%H:%M%z")
        }


class StatDetailSchema(BaseModel):
    stat_name: str
    stat_value: str


class CharacterStatSchema(BaseModel):
    date: Optional[datetime]
    character_class: str
    final_stat: List[StatDetailSchema]
    remain_ap: int

    class Config:
        orm_mode = True

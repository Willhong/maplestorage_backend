from pydantic import BaseModel
from typing import List


class CharacterSchema(BaseModel):
    ocid: str
    character_name: str
    world_name: str
    character_class: str
    character_level: int


class AccountSchema(BaseModel):
    account_id: str
    character_list: List[CharacterSchema]


class CharacterListSchema(BaseModel):
    account_list: List[AccountSchema]

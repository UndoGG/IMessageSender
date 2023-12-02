# -*- coding: windows-1251 -*-
from pydantic import BaseModel
from typing import List


class SendTime(BaseModel):
    from_hour: int
    to_hour: int


class Settings(BaseModel):
    message: str
    message_delay: int
    send_time: SendTime
    numbers: List[str]

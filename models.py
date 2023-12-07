# -*- coding: windows-1251 -*-
from pydantic import BaseModel
from typing import List


class SendTime(BaseModel):
    from_hour: int
    to_hour: int


class DelayTime(BaseModel):
    from_seconds: int
    to_seconds: int


class Settings(BaseModel):
    messages: List[str]
    message_delay: DelayTime
    send_time: SendTime
    numbers: List[str]

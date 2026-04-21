from pydantic import BaseModel, Field
import re

class Structure(BaseModel):
    tldr: str = Field(description="generate a too long; didn't read summary")
    translated_abstract: str = Field(description="complete Chinese translation of the paper abstract")
    motivation: str = Field(description="describe the motivation in this paper")
    method: str = Field(description="method of this paper")
    result: str = Field(description="result of this paper")
    conclusion: str = Field(description="conclusion of this paper")
    msc_code: str = Field(description="最相关的 MSC 2020 分类代码（如 35Bxx, 35Q30, 35K55 等），基于论文内容判断，只给出一个最相关的主代码")

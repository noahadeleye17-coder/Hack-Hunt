from datetime import date

from hackhunt.config import Settings
from hackhunt.models import Hackathon

TODAY = date(2026, 11, 15)


def make(**kw) -> Hackathon:
    defaults = dict(id="devpost:1", source="devpost", title="Test Hack", url="https://x.devpost.com/",
                    online=True, end_date=date(2026, 12, 1))
    defaults.update(kw)
    return Hackathon(**defaults)


def settings(**kw) -> Settings:
    defaults = dict(exclude_phrases=["us residents only", "not open to students"],
                    interests={"AI/agents": ["machine learning/ai", "ai", "agents"],
                               "Go": ["golang"], "Fintech": ["fintech"]})
    defaults.update(kw)
    return Settings(**defaults)

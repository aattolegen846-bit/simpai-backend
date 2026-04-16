from typing import Dict, List

from app.models.schemas import SynonymLevel, SynonymLevelResult, SynonymResponse


_SYNONYM_DB: Dict[str, Dict[SynonymLevel, List[str]]] = {
    "good": {
        SynonymLevel.level_1: ["nice", "fine", "okay"],
        SynonymLevel.level_2: ["great", "pleasant", "decent"],
        SynonymLevel.level_3: ["excellent", "favorable", "beneficial"],
        SynonymLevel.level_4: ["exemplary", "outstanding", "superlative"],
    },
    "bad": {
        SynonymLevel.level_1: ["poor", "wrong", "awful"],
        SynonymLevel.level_2: ["unpleasant", "harmful", "inferior"],
        SynonymLevel.level_3: ["detrimental", "substandard", "adverse"],
        SynonymLevel.level_4: ["deplorable", "egregious", "abysmal"],
    },
    "say": {
        SynonymLevel.level_1: ["tell", "speak", "talk"],
        SynonymLevel.level_2: ["mention", "state", "express"],
        SynonymLevel.level_3: ["articulate", "declare", "remark"],
        SynonymLevel.level_4: ["enunciate", "proclaim", "stipulate"],
    },
}


class SynonymService:
    def get_synonyms_by_levels(self, word: str, language: str = "en") -> SynonymResponse:
        normalized = word.strip().lower()
        synonym_levels = _SYNONYM_DB.get(normalized)

        if synonym_levels is None:
            synonym_levels = {
                SynonymLevel.level_1: [normalized],
                SynonymLevel.level_2: [f"more {normalized}"],
                SynonymLevel.level_3: [f"highly {normalized}"],
                SynonymLevel.level_4: [f"{normalized} (formal register)"],
            }

        levels = [
            SynonymLevelResult(
                level=level,
                words=list(dict.fromkeys(words))[:4],
                usage_hint=self._hint_for_level(level),
            )
            for level, words in synonym_levels.items()
        ]

        return SynonymResponse(
            query=normalized,
            language=language.lower(),
            levels=levels,
            notes={
                "level_1_basic": "Common daily words",
                "level_2_common": "Frequently used in work/study",
                "level_3_nuanced": "Context-sensitive synonyms",
                "level_4_advanced": "Formal and advanced lexical options",
            },
            context_examples=[
                f"Daily: The lesson was {levels[0].words[0]}.",
                f"Work: The outcome was {levels[1].words[0]}.",
                f"Academic: The effect was {levels[2].words[0]}.",
                f"Formal: The performance was {levels[3].words[0]}.",
            ],
        )

    @staticmethod
    def _hint_for_level(level: SynonymLevel) -> str:
        hints = {
            SynonymLevel.level_1: "Use in daily chat and beginner speaking.",
            SynonymLevel.level_2: "Use in school or workplace contexts.",
            SynonymLevel.level_3: "Use when precision of meaning matters.",
            SynonymLevel.level_4: "Use in formal writing, presentations, and exams.",
        }
        return hints[level]

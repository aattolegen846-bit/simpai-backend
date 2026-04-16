from app.models.schemas import SentenceUsageRequest, SentenceUsageResponse


class SentenceUsageService:
    def analyze(self, payload: SentenceUsageRequest) -> SentenceUsageResponse:
        sentence = payload.sentence.strip()
        scenario = payload.scenario.strip().lower()
        tokens = sentence.lower().split()

        register = "neutral"
        if any(token in sentence.lower() for token in ("dear", "sincerely", "regards")):
            register = "formal"
        if any(token in sentence.lower() for token in ("wanna", "gonna", "buddy", "hey")):
            register = "informal"

        usage_rule = (
            "Use this sentence when the topic and tone match your conversation context."
        )
        when_to_use = [
            f"In {scenario} context where listener expects {register} tone.",
            "When you need clear and direct communication.",
            "When sentence tense matches the real timeline of the event.",
        ]
        when_not_to_use = [
            "Do not use in high-formality situations if slang words are present.",
            "Do not use if the audience is unfamiliar with abbreviations.",
            "Avoid if cultural context can change meaning negatively.",
        ]
        alternatives = [
            "Could you please clarify this?",
            "Let me explain this in another way.",
            "I would like to confirm if this is correct.",
        ]
        risk_flags = []
        if len(tokens) > 22:
            risk_flags.append("sentence_too_long_for_spoken_context")
        if register == "informal" and scenario in ("work", "email", "interview"):
            risk_flags.append("register_mismatch")
        if any(short in sentence for short in ("lol", "u ", "idk")):
            risk_flags.append("abbreviation_risk")

        confidence_score = 0.82
        if risk_flags:
            confidence_score -= min(0.32, len(risk_flags) * 0.12)
        if register == "neutral":
            confidence_score += 0.06

        return SentenceUsageResponse(
            sentence=sentence,
            language=payload.target_language.lower(),
            scenario=scenario,
            register=register,
            usage_rule=usage_rule,
            when_to_use=when_to_use,
            when_not_to_use=when_not_to_use,
            alternatives=alternatives,
            confidence_score=round(max(0.2, min(0.99, confidence_score)), 2),
            risk_flags=risk_flags,
        )

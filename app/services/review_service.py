from typing import List, Optional

from app.database import db
from app.models.db_models import MistakeEvent, UserVocabulary


class ReviewService:
    @staticmethod
    def get_mistake_review_session(user_id: int, limit: int = 10) -> dict:
        """
        Generates a review session based on the user's most recent mistakes (Alem style).
        """
        mistakes = MistakeEvent.query.filter_by(user_id=user_id).order_by(MistakeEvent.created_at.desc()).limit(limit).all()
        
        if not mistakes:
            return {"message": "No mistakes to review! You're doing great.", "tasks": []}
            
        review_tasks = []
        for m in mistakes:
            # Generate a 'gaps' or 'correction' task for each mistake
            review_tasks.append({
                "type": "correction",
                "skill": m.skill,
                "original_error": m.user_answer,
                "expected": m.expected_answer,
                "context_instruction": f"Review your mistake in {m.skill}:"
            })
            
        return {
            "session_type": "mistake_review",
            "title": "Your Mistake Collection",
            "tasks": review_tasks
        }

    @staticmethod
    def update_vocabulary(user_id: int, word: str, is_correct: bool):
        """
        Updates word-level mastery (Duolingo style).
        """
        vocab = UserVocabulary.query.filter_by(user_id=user_id, word=word).first()
        if not vocab:
            vocab = UserVocabulary(user_id=user_id, word=word)
            db.session.add(vocab)
            
        if is_correct:
            # Increase mastery score using EMA-like approach
            vocab.mastery_score = min(1.0, vocab.mastery_score + 0.2)
        else:
            vocab.mastery_score = max(0.0, vocab.mastery_score - 0.1)
            vocab.mistake_count += 1
            
        db.session.commit()

    @staticmethod
    def get_vocabulary_stats(user_id: int) -> dict:
        total_words = UserVocabulary.query.filter_by(user_id=user_id).count()
        mastered_words = UserVocabulary.query.filter(UserVocabulary.user_id == user_id, UserVocabulary.mastery_score >= 0.8).count()
        learning_words = total_words - mastered_words
        
        return {
            "total_words_encountered": total_words,
            "mastered_count": mastered_words,
            "learning_count": learning_words,
            "mastery_percent": round((mastered_words / total_words * 100), 1) if total_words > 0 else 0
        }

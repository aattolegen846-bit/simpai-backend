from typing import List, Optional

from app.database import db
from app.models.db_models import Course, Lesson, Module, Task


class ContentService:
    @staticmethod
    def get_courses(language: Optional[str] = None) -> List[dict]:
        query = Course.query
        if language:
            query = query.filter_by(language=language)
        courses = query.all()
        return [
            {
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "language": c.language,
                "level": c.level
            }
            for c in courses
        ]

    @staticmethod
    def get_course_details(course_id: int) -> dict:
        course = db.session.get(Course, course_id)
        if not course:
            return {}
        
        modules = Module.query.filter_by(course_id=course_id).order_by(Module.order).all()
        details = {
            "id": course.id,
            "title": course.title,
            "modules": []
        }
        
        for m in modules:
            lessons = Lesson.query.filter_by(module_id=m.id).order_by(Lesson.order).all()
            details["modules"].append({
                "id": m.id,
                "title": m.title,
                "lessons": [
                    {"id": l.id, "title": l.title}
                    for l in lessons
                ]
            })
        return details

    @staticmethod
    def get_lesson_tasks(lesson_id: int) -> dict:
        lesson = db.session.get(Lesson, lesson_id)
        if not lesson:
            return {}
            
        tasks = Task.query.filter_by(lesson_id=lesson_id).order_by(Task.order).all()
        return {
            "lesson_id": lesson.id,
            "title": lesson.title,
            "tasks": [
                {
                    "id": t.id,
                    "type": t.task_type,
                    "content": t.content
                }
                for t in tasks
            ]
        }

    @staticmethod
    def seed_demo_content():
        """
        Seeds the database with 'Super Pro Demo' content for investors.
        """
        if Course.query.first():
            return  # Already seeded
            
        # Course 1: English for IT
        it_english = Course(
            title="English for IT Professionals",
            description="Master technical communication and interview skills.",
            language="English",
            level="B2"
        )
        db.session.add(it_english)
        db.session.flush()
        
        mod1 = Module(course_id=it_english.id, title="The Agile Workflow", order=1)
        db.session.add(mod1)
        db.session.flush()
        
        les1 = Lesson(module_id=mod1.id, title="Daily Stand-ups", order=1)
        db.session.add(les1)
        db.session.flush()
        
        # Tasks for Lesson 1 (EdVibe style)
        tasks = [
            Task(
                lesson_id=les1.id,
                task_type="matching",
                content={
                    "instruction": "Match the meeting type to its purpose.",
                    "pairs": [
                        {"item": "Daily Stand-up", "match": "Status updates and blockers"},
                        {"item": "Sprint Review", "match": "Demoing the increment"},
                        {"item": "Retrospective", "match": "Process improvement"}
                    ]
                },
                order=1
            ),
            Task(
                lesson_id=les1.id,
                task_type="gaps",
                content={
                    "instruction": "Complete the developer update.",
                    "text": "Yesterday I [fixed] a bug in the auth module. Today I will [implement] the new API endpoint.",
                    "options": ["fixed", "implement", "deleted", "broken"]
                },
                order=2
            )
        ]
        for t in tasks:
            db.session.add(t)
            
        # Course 2: Everyday Kazakh
        kazakh_daily = Course(
            title="Күнделікті Қазақ тілі",
            description="Базалық сөйлесу дағдылары.",
            language="Kazakh",
            level="A1"
        )
        db.session.add(kazakh_daily)
        db.session.flush()
        
        mod_k = Module(course_id=kazakh_daily.id, title="Танысу", order=1)
        db.session.add(mod_k)
        db.session.flush()
        
        les_k = Lesson(module_id=mod_k.id, title="Сәлемдесу", order=1)
        db.session.add(les_k)
        db.session.flush()
        
        task_k = Task(
            lesson_id=les_k.id,
            task_type="ordering",
            content={
                "instruction": "Put the greeting in the correct order.",
                "items": ["Сәлем", "Қалың", "қалай?", "Жақсы,", "рахмет"]
            },
            order=1
        )
        db.session.add(task_k)
        
        db.session.commit()

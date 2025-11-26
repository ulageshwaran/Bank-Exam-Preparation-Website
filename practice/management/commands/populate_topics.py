from django.core.management.base import BaseCommand
from exams.models import Topic
from practice.models import Question
from ai_engine.ai_service import generate_topic_questions
import time

class Command(BaseCommand):
    help = 'Ensures every topic has at least 10 questions'

    def handle(self, *args, **kwargs):
        topics = Topic.objects.all()
        total_topics = topics.count()
        self.stdout.write(f"Checking {total_topics} topics...")

        for i, topic in enumerate(topics):
            count = topic.questions.count()
            needed = 10 - count
            
            if needed > 0:
                self.stdout.write(f"[{i+1}/{total_topics}] '{topic.name}' has {count} questions. Generating {needed} more...")
                
                # Generate in batches of 5 to be safe
                while needed > 0:
                    batch_size = min(needed, 5)
                    questions_data = generate_topic_questions(topic.name, batch_size, 'Medium')
                    
                    if not questions_data:
                        self.stdout.write(self.style.WARNING(f"  - Failed to generate questions for '{topic.name}'. Skipping."))
                        break
                        
                    for q_data in questions_data:
                        Question.objects.create(
                            topic=topic,
                            text=q_data.get('text'),
                            option_a=q_data.get('option_a'),
                            option_b=q_data.get('option_b'),
                            option_c=q_data.get('option_c'),
                            option_d=q_data.get('option_d'),
                            option_e=q_data.get('option_e'),
                            correct_option=q_data.get('correct_option'),
                            explanation=q_data.get('explanation'),
                            difficulty='Medium',
                            is_ai_generated=True
                        )
                    
                    needed -= len(questions_data)
                    self.stdout.write(f"  - Added {len(questions_data)} questions.")
                    time.sleep(1) # Rate limiting
            else:
                self.stdout.write(f"[{i+1}/{total_topics}] '{topic.name}' already has {count} questions. OK.")
        
        self.stdout.write(self.style.SUCCESS("Population complete!"))

from django.core.management.base import BaseCommand
from exams.models import Exam, Subject, Topic
from practice.models import Question
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds initial data for the application'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding data...')

        # Create Exam
        exam, created = Exam.objects.get_or_create(
            name='SBI PO',
            defaults={'slug': 'sbi-po', 'description': 'State Bank of India Probationary Officer Exam'}
        )
        if created:
            self.stdout.write(f'Created Exam: {exam.name}')

        # Subjects and Topics
        subjects_data = {
            'Quantitative Aptitude': ['Number Series', 'Simplification', 'Quadratic Equations', 'Data Interpretation', 'Arithmetic'],
            'Reasoning Ability': ['Puzzles', 'Seating Arrangement', 'Syllogism', 'Blood Relations', 'Coding-Decoding'],
            'English Language': ['Reading Comprehension', 'Cloze Test', 'Error Spotting', 'Para Jumbles', 'Fillers'],
            'General Awareness': ['Current Affairs', 'Banking Awareness', 'Static GK'],
            'Computer Knowledge': ['Hardware', 'Software', 'Networking', 'DBMS', 'Internet']
        }

        for sub_name, topics in subjects_data.items():
            subject, created = Subject.objects.get_or_create(
                exam=exam,
                name=sub_name,
                defaults={'slug': slugify(sub_name)}
            )
            if created:
                self.stdout.write(f'  Created Subject: {subject.name}')

            for topic_name in topics:
                topic, created = Topic.objects.get_or_create(
                    subject=subject,
                    name=topic_name,
                    defaults={'slug': slugify(topic_name)}
                )
                if created:
                    self.stdout.write(f'    Created Topic: {topic.name}')
                    
                    # Create a sample question for each topic
                    Question.objects.get_or_create(
                        topic=topic,
                        text=f'Sample question for {topic_name}?',
                        defaults={
                            'option_a': 'Option A',
                            'option_b': 'Option B',
                            'option_c': 'Option C',
                            'option_d': 'Option D',
                            'option_e': 'Option E',
                            'correct_option': 'A',
                            'explanation': 'This is a sample explanation.',
                            'difficulty': 'Easy'
                        }
                    )

        self.stdout.write(self.style.SUCCESS('Data seeding completed successfully.'))

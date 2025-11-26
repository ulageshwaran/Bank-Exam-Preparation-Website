import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bank_exam_platform.settings')
django.setup()

from exams.models import Topic
from django.db.models import Count

def deduplicate_topics():
    # Find duplicates
    duplicates = Topic.objects.values('slug').annotate(count=Count('id')).filter(count__gt=1)
    
    print(f"Found {duplicates.count()} duplicate slugs.")
    
    for dup in duplicates:
        slug = dup['slug']
        topics = Topic.objects.filter(slug=slug).order_by('id')
        
        # Keep the first one, delete the rest
        primary_topic = topics.first()
        duplicates_to_delete = topics[1:]
        
        print(f"Processing '{slug}': Keeping ID {primary_topic.id}, deleting {duplicates_to_delete.count()} duplicates.")
        
        for dt in duplicates_to_delete:
            # Reassign questions to the primary topic before deleting
            dt.questions.update(topic=primary_topic)
            dt.delete()
            
    print("Deduplication complete.")

if __name__ == '__main__':
    deduplicate_topics()

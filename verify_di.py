import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bank_exam_platform.settings')
django.setup()

from ai_engine.ai_service import generate_test_questions
import json

print("Generating DI questions...")
questions = generate_test_questions('Quantitative Aptitude', 40)

di_questions = [q for q in questions if 'Data Interpretation' in q.get('topic', '')]

print(f"Generated {len(di_questions)} DI questions.")

# Verify Grouping and Chart Data
print("\n--- Verifying Grouping and Chart Data ---")

# Group by common text/chart to identify sets
sets = {}
for q in questions:
    # Use a unique key for the set (chart title or text snippet)
    key = "Unknown"
    chart_type = "None"
    
    if q.get('chart_data'):
        key = q['chart_data'].get('title', 'Untitled Chart')
        chart_type = q['chart_data'].get('type', 'Unknown')
    elif q.get('passage'):
         key = q['passage'][:30] + "..."
         
    if key not in sets:
        sets[key] = {'count': 0, 'type': chart_type}
    sets[key]['count'] += 1

print(f"\nIdentified {len(sets)} unique sets:")
for key, data in sets.items():
    print(f"  - Set '{key}': {data['count']} questions (Type: {data['type']})")
    
# Check for variety (manual check based on output)
print("\nCheck the output above to ensure different chart types (table, bar, line, pie) are generated across multiple runs.")

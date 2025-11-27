import PyPDF2
import sys

pdf_path = r'c:\Users\ULAGESHWARAN E\python\bank exam\rrb_clerk_mock_test[1].pdf'

with open(pdf_path, 'rb') as pdf_file:
    reader = PyPDF2.PdfReader(pdf_file)
    
    # Extract first 15 pages
    for i, page in enumerate(reader.pages[:15]):
        text = page.extract_text()
        print(f"\n{'='*80}")
        print(f"PAGE {i+1}")
        print(f"{'='*80}\n")
        # Encode to utf-8 to handle special characters
        sys.stdout.buffer.write(text.encode('utf-8'))
        print("\n")

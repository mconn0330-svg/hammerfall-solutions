import sys
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import date

def extract_text(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as docx:
            xml_content = docx.read('word/document.xml')
        tree = ET.fromstring(xml_content)
        namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        paragraphs = []
        for p in tree.findall('.//w:p', namespaces):
            texts = [node.text for node in p.findall('.//w:t', namespaces) if node.text]
            if texts:
                paragraphs.append(''.join(texts))
            else:
                paragraphs.append('')
        return '\n'.join(paragraphs)
    except Exception as e:
        return ""

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    codename = os.path.basename(os.path.normpath(input_dir))
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for filename in os.listdir(input_dir):
        if filename.endswith(".docx"):
            path = os.path.join(input_dir, filename)
            text = extract_text(path)
            
            # Determine type
            doc_type = "Spec"
            lower_name = filename.lower()
            if "prd" in lower_name: doc_type = "PRD"
            elif "blueprint" in lower_name: doc_type = "Blueprint"
            elif "style" in lower_name and "guide" in lower_name: doc_type = "StyleGuide"
            
            # Write frontmatter
            out_filename = filename.replace(".docx", ".md")
            out_path = os.path.join(output_dir, out_filename)
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(f"source: {filename}\n")
                f.write(f"captured: {date.today().isoformat()}\n")
                f.write(f"type: {doc_type}\n")
                f.write(f"project: {codename}\n")
                f.write("status: pending\n")
                f.write("---\n\n")
                f.write(text)

if __name__ == "__main__":
    main()

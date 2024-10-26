from flask import Flask, request, render_template_string
from pdf2image import convert_from_path
import pytesseract
import os
import re
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

# HTML template for upload form
upload_form_html = '''
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Upload 10th Marksheet PDF</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #e6f7ff; padding: 20px; }
        .form-container { background-color: #f9f9f9; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; }
        .field-row { margin-bottom: 10px; }
        label { display: inline-block; width: 150px; }
        input[type="text"] { width: 100px; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>Upload Your 10th Marksheet PDF</h1>
        <form method="post" action="/upload" enctype="multipart/form-data">
            <input type="file" name="file" accept="application/pdf" required>
            <input type="submit" value="Upload">
        </form>
    </div>
</body>
</html>
'''

@app.route('/')
def upload_form():
    return render_template_string(upload_form_html)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file uploaded', 400
    file = request.files['file']
    if file.filename == '':
        return 'No file selected', 400

    # Create a unique filename using timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    original_filename = file.filename
    file_extension = os.path.splitext(original_filename)[1]
    new_filename = f"{os.path.splitext(original_filename)[0]}_{timestamp}{file_extension}"
    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

    # Save the uploaded PDF
    file.save(pdf_path)

    # Convert PDF to images
    images = convert_from_path(pdf_path)

    # Perform OCR on each image and extract marks
    extracted_marks_dict = {}
    optional_subject_name = None
    optional_subject_mark = None
    subjects = ['Tamil', 'English', 'Mathematics', 'Science', 'Social Science', 'Total Marks']  # Primary subjects
    marks = []

    # OCR extraction
    for img in images:
        text = pytesseract.image_to_string(img)
        marks += re.findall(r'\b\d{1,3}\b', text)

        # Check for optional subject and its marks using keywords (e.g., 'Computer Science')
        optional_match = re.search(r'Optional Subject: ([A-Za-z\s]+)\s+(\d{1,3})', text)
        if optional_match:
            optional_subject_name = optional_match.group(1).strip()
            optional_subject_mark = optional_match.group(2).strip()

    # Assign marks to predefined subjects
    for i, subject in enumerate(subjects):
        if i < len(marks):
            extracted_marks_dict[subject] = marks[i]
        else:
            extracted_marks_dict[subject] = 0  # Default to 0 if not enough marks found

    # Add optional subject mark if found
    if optional_subject_name and optional_subject_mark:
        extracted_marks_dict['Optional Subject Name'] = optional_subject_name
        extracted_marks_dict['Optional Subject Mark'] = optional_subject_mark

    # Clean up the uploaded file
    os.remove(pdf_path)

    # Generate HTML output with read-only fields and optional subject checkbox
    form_html = f'''
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Extracted Marks</title>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #e6f7ff; padding: 20px; }}
            .form-container {{ background-color: #f9f9f9; padding: 20px; border-radius: 8px; max-width: 400px; margin: auto; }}
            .field-row {{ margin-bottom: 10px; }}
            label {{ display: inline-block; width: 150px; }}
            input[type="text"] {{ width: 100px; }}
        </style>
    </head>
    <body>
        <div class="form-container">
            <h1>Extracted Marks</h1>
            <form action="/finalize" method="post">
    '''
    for subject, marks in extracted_marks_dict.items():
        form_html += f'''
            <div class="field-row">
                <label for="{subject}">{subject} :</label>
                <input type="text" id="{subject}" name="{subject}" value="{marks}" readonly>
            </div>
        '''
    
    # Adding checkbox and read-only input fields for optional language
    form_html += f'''
            <div class="field-row">
                <label>
                    <input type="checkbox" id="optional_subject_checkbox" name="optional_subject_checkbox" value="true" onchange="toggleOptionalFields()"> Optional Language
                </label>
            </div>
            <div class="field-row">
                <label for="optional_subject_name">Subject Name :</label>
                <input type="text" id="optional_subject_name" name="optional_subject_name" value="{optional_subject_name or ''}" readonly>
            </div>
            <div class="field-row">
                <label for="optional_subject_mark">Subject Mark :</label>
                <input type="text" id="optional_subject_mark" name="optional_subject_mark" value="{optional_subject_mark or ''}" readonly>
            </div>
            <div class="field-row">
                <label for="total_marks">Total Marks :</label>
                <input type="text" id="total_marks" name="total_marks" value="{extracted_marks_dict.get('Total Marks', '')}" readonly>
            </div>
            <input type="submit" value="Finalize">
            </form>
        </div>
        <script>
            function toggleOptionalFields() {{
                const isChecked = document.getElementById("optional_subject_checkbox").checked;
                document.getElementById("optional_subject_name").style.display = isChecked ? 'block' : 'none';
                document.getElementById("optional_subject_mark").style.display = isChecked ? 'block' : 'none';
            }}
            window.onload = toggleOptionalFields;
        </script>
    </body>
    </html>
    '''

    return form_html  # Return the HTML form as response

@app.route('/finalize', methods=['POST'])
def finalize_marks():
    # Prepare final output
    final_output = f'<h1>Final Extracted Marks:</h1><pre>'
    for subject, value in request.form.items():
        final_output += f"{subject}: {value}\n"

    final_output += '</pre>'
    
    return final_output

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)

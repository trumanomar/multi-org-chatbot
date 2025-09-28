import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet


# --- Utility function to create a PDF ---
def create_pdf(filename, paragraphs):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(filename, pagesize=A4)
    story = []

    for para in paragraphs:
        story.append(Paragraph(para, styles["Normal"]))
        story.append(Spacer(1, 12))

    doc.build(story)


# --- Output folder ---
output_dir = "medical_pdfs"
os.makedirs(output_dir, exist_ok=True)

# --- Define medical documents content ---
documents = {
    "hospitals.pdf": [
        "Dr. Alice founded MedCare Hospital in 2015.",
        "Dr. Bob is the Head of Cardiology at MedCare Hospital.",
        "MedCare Hospital partnered with GreenHealth Clinic in 2020.",
        "GreenHealth Clinic was established by Dr. Carol in 2018."
    ],
    "treatments.pdf": [
        "MedCare Hospital provides HeartShield Therapy.",
        "HeartShield Therapy is used for treating Hypertension.",
        "GreenHealth Clinic provides EcoTherapy.",
        "EcoTherapy competes with HeartShield Therapy."
    ],
    "events.pdf": [
        "In 2021, MedCare Hospital hosted the Global Health Conference in Berlin.",
        "GreenHealth Clinic presented EcoTherapy at the Global Health Conference.",
        "The Global Health Conference was attended by Dr. Alice and Dr. Carol."
    ],
    "locations.pdf": [
        "MedCare Hospital headquarters is in Berlin.",
        "GreenHealth Clinic headquarters is in Paris.",
        "Berlin is in Germany.",
        "Paris is in France.",
        "Germany borders France."
    ],
    "research.pdf": [
        "Dr. Alice published 'Advances in Hypertension Treatment' in 2022.",
        "'Advances in Hypertension Treatment' cites 'Sustainable Cardiology' by Dr. Bob.",
        "Dr. Carol authored 'Eco-friendly Therapies' in 2021.",
        "'Eco-friendly Therapies' was presented at the Global Health Conference."
    ]
}

# --- Generate PDFs ---
for filename, content in documents.items():
    filepath = os.path.join(output_dir, filename)
    create_pdf(filepath, content)

print(f"✅ Generated {len(documents)} medical PDFs in folder: {output_dir}")

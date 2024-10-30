import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def process_pdf_data(pdf_text):
    lines = pdf_text.split('\n')
    
    st.write(f"Total lines in PDF: {len(lines)}")  # Debug info
    
    # Skip the header and remove empty lines
    data_lines = [line.strip() for line in lines[1:] if line.strip()]
    
    processed_data = []
    for line in data_lines:
        parts = line.split()
        if len(parts) >= 11:  # Ensure we have all required fields
            try:
                name = parts[0]
                total_salary = float(parts[1].replace(',', ''))
                salary_per_hour = float(parts[2].replace(',', ''))
                hours = [int(h) for h in parts[3:10]]
                total_hours = int(parts[10])
                
                processed_data.append([name, total_salary, salary_per_hour] + hours + [total_hours])
            except (ValueError, IndexError) as e:
                st.warning(f"Skipping invalid data: {line}. Error: {str(e)}")
    
    if not processed_data:
        st.error("No valid data found in the PDF. Please check the file format.")
        return None
    
    columns = ['Name', 'Total Salary', 'Salary per hour'] + [f'{i}/09/2024' for i in range(1, 8)] + ['Total Hours']
    df = pd.DataFrame(processed_data, columns=columns)
    
    st.write(f"Processed entries: {len(df)}")  # Debug info
    return df

def calculate_deductions(df, threshold_hours):
    results = []
    for _, row in df.iterrows():
        worked_hours = row['Total Hours']
        if worked_hours >= threshold_hours:
            deduction = 0
        else:
            deduction = (threshold_hours - worked_hours) * row['Salary per hour']
        
        results.append({
            'Name': row['Name'],
            'Total Salary': row['Total Salary'],
            'Worked Hours': worked_hours,
            'Threshold Hours': threshold_hours,
            'Deduction': deduction,
            'Final Salary': row['Total Salary'] - deduction
        })
    
    return pd.DataFrame(results)

def create_pdf(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # Convert DataFrame to formatted strings for PDF
    formatted_df = df.copy()
    formatted_df['Total Salary'] = formatted_df['Total Salary'].apply(lambda x: f"{x:.2f}")
    formatted_df['Deduction'] = formatted_df['Deduction'].apply(lambda x: f"{x:.2f}")
    formatted_df['Final Salary'] = formatted_df['Final Salary'].apply(lambda x: f"{x:.2f}")

    data = [df.columns.tolist()] + formatted_df.values.tolist()
    table = Table(data)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)
    
    try:
        doc.build(elements)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None

def main():
    st.title("Salary Calculator App")

    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    
    if uploaded_file is not None:
        try:
            pdf_text = extract_text_from_pdf(uploaded_file)
            
            with st.expander("Show extracted PDF text"):
                st.text(pdf_text[:500] + "..." if len(pdf_text) > 500 else pdf_text)
            
            df = process_pdf_data(pdf_text)
            
            if df is not None and not df.empty:
                st.subheader("Extracted Data")
                st.dataframe(df)
                
                threshold_hours = st.number_input("Enter the threshold hours:", min_value=0, value=40, step=1)
                
                if st.button("Calculate Deductions"):
                    result_df = calculate_deductions(df, threshold_hours)
                    
                    st.subheader("Salary Deductions")
                    st.dataframe(result_df.style.format({
                        'Total Salary': '{:.2f}',
                        'Worked Hours': '{:.0f}',
                        'Threshold Hours': '{:.0f}',
                        'Deduction': '{:.2f}',
                        'Final Salary': '{:.2f}'
                    }))
                    
                    pdf_buffer = create_pdf(result_df)
                    if pdf_buffer:
                        st.download_button(
                            label="Download PDF Report",
                            data=pdf_buffer,
                            file_name="salary_deductions.pdf",
                            mime="application/pdf"
                        )
            else:
                st.error("Unable to process the PDF. Please ensure it contains valid data in the correct format.")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
    else:
        st.info("Please upload a PDF file to begin processing.")

if __name__ == "__main__":
    main()
import tabula
import fitz
import pandas as pd
import re

pdf_path = r'pdfs/2024 08 test res 4.PDF'

tbs = tabula.read_pdf(pdf_path, pages = 1)  
#len(tbs)
#tb = tbs[0]
output = tabula.convert_into(r'C:\Users\joyjp\Desktop\Carte Clinics Project\pdf_to_sheet_project\pdf_files\pdfs/2024 08 test res 4.PDF', "converted3.csv", output_format = "csv", pages = [1] )
#print(tb)
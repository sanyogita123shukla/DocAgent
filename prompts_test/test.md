

# quesionaire:
```
Please analyze the uploaded document. First, provide a detailed summary of what this document is and its purpose. Second, evaluate if this is a questionnaire or form. If it is, extract every single question asked in the document and present them in a numbered list
```

# excel:
```
Summarize file structure (sheets, headers, types) and purpose. Detect if this is a form or a dataset. List questions sequentially if it's a form, or primary identifiers if it's data
```


____
🏎️ Scenario 1: The "Messy" Data Audit (Excel)
Prompt:

"Analyze this data for quality and consistency. I need to know if we can trust this dataset for reporting. Identify any duplicates, empty columns, or mixed data types."

____
📰 Scenario 2: Complex Document Extraction (PDF)
Prompt:

"Provide a detailed executive summary of this document and extract all internal tables into a clean markdown format. Ensure you preserve the reading order of the columns."

____
📑 Scenario 3: The Hybrid Document Intent (PDF)
Prompt:

"Classify the intent of this document. Then, identify if there are any specific form fields, questions, or registration items I need to address."

____
🧠 Scenario 4: Deep Context & Persistence (Follow-up)
Query 1 (Initial):

"Summarize the key sections and list the top 2 highest values found." Query 2 (Follow-up - No re-upload): "What is the percentage difference between the first and last value you just listed?"


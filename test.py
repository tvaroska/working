from vertexai.generative_models import GenerativeModel, Content, Part

FILE_NAME = '/tmp/flet/9751/2312.10997v5.pdf'

writer_model = GenerativeModel(model_name='gemini-1.5-flash-001', system_instruction='Create summary of the paper. When you get the feedback respond with the updated summary.')
review_model = GenerativeModel(model_name='gemini-1.5-flash-001', system_instruction='Review user submitted summary of the paper. Provide concise, actionable feedback which can user utilize to improve the summary')

with open(FILE_NAME, 'rb') as f:
    pdf = Part.from_data(f.read(), 'application/pdf')

summaries = []
writer = [Content(role='USER', parts=[
    Part.from_text('<PAPER>'), 
    pdf, 
    Part.from_text('</PAPER>')])]
reviewer = []

for i in range(3):
    writer_response = writer_model.generate_content(writer)
    reviewer.append(Content(role='USER', parts=[pdf, writer_response.candidates[0].content.parts[0]]))
    writer.append(Content(role='MODEL', parts=[writer_response.candidates[0].content.parts[0]]))
    summaries.append(writer_response.candidates[0].content.parts[0].text)

    reviewer_response = review_model.generate_content(reviewer)
    writer.append(Content(role='USER', parts=[reviewer_response.candidates[0].content.parts[0]]))
    reviewer.append(Content(role='MODEL', parts=[reviewer_response.candidates[0].content.parts[0]]))

pass
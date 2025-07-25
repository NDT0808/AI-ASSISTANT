﻿

# Import required libraries:
# --------------------------
import os # Standard Library
import tempfile

# Our Own Modules
from lib import chatpdf, chatgeneration, sidebar

# Third-Party Libraries
from dotenv import load_dotenv
import streamlit as st
from pypdf import PdfReader, PdfWriter
import fitz # PyMuPDF
from pdf4llm import to_markdown

# ------------------------------------------------------------------------------

# Models:
# -------
models = [
  'command-r-plus',
  'llama-3.3-70b-versatile'
  ]
# -----------------------------------------------------------------------------


# Load Environment Variables:
# ---------------------------
load_dotenv()

openai_api_key = os.getenv('OPENAI_API_KEY')
anthropic_api_key = os.getenv('ANTHROPIC_API_KEY')
cohere_api_key = os.getenv('COHERE_API_KEY')
groq_api_key = os.getenv('GROQ_API_KEY')
# -----------------------------------------------------------------------------


# Constant Values:
# ----------------
TEMPERATURE = 0.25
MAX_PDF_PAGES = 30

# -----------------------------------------------------------------------------
# Manage page tracking and associated session state
# -----------------------------------------------------------------------------
THIS_PAGE = "exam_ally"
if "cur_page" not in st.session_state:
    st.session_state.cur_page = THIS_PAGE

if ("token_counts" not in st.session_state) or (st.session_state.cur_page != THIS_PAGE):
    st.session_state.token_counts = {model: {"input_tokens": 0, "output_tokens": 0} for model in models}

if ("submitted" not in st.session_state) or (st.session_state.cur_page != THIS_PAGE):
    st.session_state.submitted = False

# purge messages when entering the page
if (st.session_state.cur_page != THIS_PAGE) and ("messages" in st.session_state):
  del st.session_state.messages

st.session_state.cur_page = THIS_PAGE
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------

# Streamlit Application:
# ----------------------
st.set_page_config(page_title = "ChatISA Exam Ally", layout = "centered",page_icon='🤖')
st.markdown("## 🤖 ChatISA: Exam Ally 🤖")


# First "Screen" of the Exam Ally:
# --------------------------------
if not st.session_state.submitted:
    st.markdown(
        "Welcome to ChatISA Exam Ally! This tool is designed to help you prepare "
        "for your exams by generating practice questions based a PDF document that you upload. "
        "The PDF can be an electronic textbook, lecture notes, or any other study material that you have. "
        "Once you upload the PDF, provide which type of exam questions you would like to generate. "
        "With only these two components, the tool will generate a personalized exam with questions that you can use to practice. "
        "Please note that the questions are generated by a language model and may not be perfect. "
        "Therefore, we strongly suggest that you use this tool as a final prepatory stage prior to your exam." 
        "Good luck with your studies!"
        )
    
    st.sidebar.markdown("### Choose Your LLM")
    model_choice = st.sidebar.selectbox(
      "Choose your LLM",
      models,
      index= 0,
      key='model_choice',
      label_visibility='collapsed',
      help="Choose the LLM you want to use for generating the exam questions."
      ) 
      
    col1, col2 = st.columns(2, gap = 'large')

    with col1:
      st.markdown("### Course Material")
      
      course_doc = st.file_uploader(
        "Upload your PDF file",
        type = ['pdf'],
        key = 'course_doc',
        help = "Upload your course material in PDF format. This will be used to generate relevant exam questions."
        )
      
    with col2:
      st.markdown('### Exam Question Type')
      
      exam_type = st.selectbox(
        "Choose the type of exam questions you want to generate",
        ["Conceptual Multiple Choice", "Conceptual Short Answer", "Code Understanding", "Data Analysis"],
        index= 0,
        key='exam_type',
        help="Choose the type of exam questions you want to generate."
        )
      
    if st.button('Submit'):
        if all([model_choice, course_doc, exam_type]):
            # Process the course material
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(course_doc.getvalue())
                tmp_path = tmp.name

            infile = PdfReader(tmp_path, "rb")

            if len(infile.pages) > MAX_PDF_PAGES:
                output = PdfWriter()
                for i in range(MAX_PDF_PAGES):
                   output.add_page(infile.pages[i])
                with open(tmp_path, "wb") as f:
                   output.write(f)
            
            infile = PdfReader(tmp_path, "rb")

            course_text = to_markdown(tmp_path)
            os.unlink(tmp_path)

            # Store information in session_state
            st.session_state['submission'] = {
                'model_choice': model_choice,
                'course_text': course_text,
                'exam_type': exam_type
            }
            
            # Clear the form or redirect/show other content
            st.success('Your submission has been recorded.')
            st.session_state.submitted = True
            st.rerun()
          
        else:
            st.error('Please fill in all fields before submitting.')

# -----------------------------------------------------------------------------
# Render the sidebar
# -----------------------------------------------------------------------------
sidebar.render_sidebar()
# -----------------------------------------------------------------------------

# Next Screen:
# ------------
if st.session_state.submitted:
    # Retrieve the information from the session_state
    model_choice = st.session_state.submission['model_choice']
    course_text = st.session_state.submission['course_text']
    exam_type = st.session_state.submission['exam_type']
    
    # The system prompt
    SYSTEM_PROMPT = (
      "You will be acting as an AI tutor to help students prepare for an information "
      "systems and analytics exam. You will be provided with a course document that may "
      "be a textbook, lecture notes, or study guide. Your goal is to generate "
      "practice exam questions for the student based: (a) their uploaded course document, "
      "and (b) their chosen exam question style. \n\n"
      "#Course Document:\n"
      f"{course_text}\n\n"
      "#Exam Question Style:\n"
      f"{exam_type}\n\n"
      "Generate exam questions using the following criteria:\n"
      "- If the student requested short-answer questions, generate 10 questions that "
      "cover a range of topics from the documents.\n"
      "- For all other question types, generate 4-5 questions.\n"
      "- Show one question at a time and wait for the student to provide an answer "
      "before moving on to the next question.\n\n"
      "Once you receive the student's answer, acknowledge it and present the next "
      "question. Continue this process until the student has answered all of the "
      "questions you generated.\n\n"
      "After the student has completed all the questions, provide them with the "
      "following:\n"
      "1. In a <feedback> block, write a detailed evaluation of their performance on "
      "each question. Structure your feedback as follows:\n"
      "- Begin with an overall summary paragraph highlighting areas of strength and "
      "areas for improvement.\n"
      "- Then, go through each of their answers, first restating the question, then "
      "assessing the correctness and completeness of their answer. Provide guidance on "
      "how they could improve their answer if applicable.\n"
      "- End with some motivating words of encouragement.\n\n"
      "2. After the <feedback> block, provide their overall exam score in a <score> "
      "block. Calculate the score as follows:\n"
      "- Divide 100 points evenly across all questions (e.g. if there were 10 "
      "questions, each one is worth 10 points).\n"
      "- Award points for each question based on the correctness and completeness of "
      "the student's answer.\n"
      "- Sum up the points and provide a final score out of 100.\n\n"
      "Some key things to remember:\n"
      "- Be patient and encouraging in your tone. The goal is to help the student "
      "learn and feel more prepared for their exam.\n"
      "- Provide detailed and constructive feedback, pointing out both strengths and "
      "weaknesses in their answers.\n"
      "- Generate questions that test a range of concepts and skills from the course "
      "documents.\n"
      "- Do not show the student the questions in advance; they should be seeing them "
      "for the first time when you present them in a one-question-at-a-time format."
    )

    
    # Generate the interview questions
    if "messages" not in st.session_state:
      st.session_state.messages = [{
        "role": "system",
        "content": SYSTEM_PROMPT
      },{
        "role": "user", 
        "content": "Hello, please help me prepare for my exam."
        }]
      
    for message in st.session_state.messages[2:]:
      with st.chat_message(message["role"]):
        st.markdown(message["content"])

    # Display chatbox input & process user input
    if prompt := st.chat_input("To start, type Hi. Then, answer the questions throughoutfully."):
      # Store the user's prompt to memory
      st.session_state.messages.append({"role": "user", "content": prompt})
      # Display the user's prompt to the chat window
      st.chat_message("user").markdown(prompt)
      # Stream response from the LLM
      with st.chat_message("assistant"):
        
        # initializing the response objects
        message_placeholder = st.empty()
        full_response = ""
        input_token_count = 0
        output_token_count = 0
        
        # generating the response
        outputs = chatgeneration.generate_chat_completion(
          model = st.session_state.submission['model_choice'],
          messages = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages
                ],
          temp = TEMPERATURE,
          max_num_tokens = 3000
        )
        
        # extracting the response, input tokens, and output tokens
        response, input_tokens, output_tokens = outputs
        full_response += response
        message_placeholder.markdown(full_response + "▌")
        
        # Update the token counts for the specific model in session state
        st.session_state.token_counts[st.session_state.submission['model_choice']]['input_tokens'] += input_tokens
        st.session_state.token_counts[st.session_state.submission['model_choice']]['output_tokens'] += output_tokens
      
      # Store the full response from the LLM in memory
      st.session_state.messages.append({"role": "assistant", "content": full_response})



  
    # Generating the PDF from the Chat:
    # ---------------------------------
    with st.expander("Export Chat to PDF"):
      row = st.columns([2, 2])
      user_name = row[0].text_input("Enter your name:")
      user_name = user_name.replace(" ", "_")
      user_course = row[1].text_input("Enter course name:")
      user_course = user_course.replace(" ", "_")
      if user_name != "" and user_course != "":
        pdf_output_path = chatpdf.create_pdf(chat_messages=st.session_state.messages, models = models, token_counts = st.session_state.token_counts, user_name=user_name, user_course=user_course)

        with open(pdf_output_path, "rb") as file:
          st.download_button(label="Download PDF", data=file, file_name=f"{user_course}_{user_name}_chatisa.pdf", mime="application/pdf", use_container_width=True)

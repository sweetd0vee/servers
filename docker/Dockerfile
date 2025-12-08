FROM python:3.12-slim

RUN mkdir /work

COPY ./requirements.txt /work
COPY ./app/*.py /work

WORKDIR /work

RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements.txt

# Expose the default Streamlit port
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

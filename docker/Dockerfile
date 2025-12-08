FROM python:3.12-slim

RUN mkdir /work
RUN mkdir /work/data

COPY ./requirements.txt /work
COPY ./app/*.py /work
COPY ./data/* /work/data

WORKDIR /work

RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements.txt

CMD ["streamlit", "run", "app.py"]

FROM python:3.12-slim

RUN mkdir /work

WORKDIR /work

COPY ./requirements.txt /work
RUN pip install --no-cache-dir --timeout 1000 --retries 5 -r requirements.txt


RUN mkdir /work/app
RUN mkdir /work/assets
RUN mkdir /work/data
RUN mkdir /work/database
RUN mkdir /work/schemas


COPY ./app/*.py /work/app
COPY ./assets/* /work/assets
#COPY ./data/* /work/data
COPY ./database/* /work/database
COPY ./schemas/* /work/schemas

COPY ./base_logger.py /work

WORKDIR /work/app

CMD ["streamlit", "run", "app.py"]

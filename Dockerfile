FROM rokubun/python:numpy-slim-buster AS dependencies

WORKDIR /gnss_benchmark
COPY requirements.txt .

RUN apt-get update \
 && apt-get install -y pandoc texlive  \
 && pip install --upgrade pip \
 && pip install -r requirements.txt

FROM dependencies 

COPY . .

RUN python setup.py install

CMD ["gnss_benchmark","make_report"]


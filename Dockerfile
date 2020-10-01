FROM rokubun/python:numpy-slim-buster AS production


WORKDIR /gnss_benchmark
COPY . .
 

RUN apt-get update \
 && apt-get install -y pandoc \
 && pip install --upgrade pip \
 && pip install jason-gnss roktools pyproj Jinja2 \
 && pip install .

CMD ["gnss_benchmark","make_report", "-o", "/workdir", "-r", "report.pdf"]


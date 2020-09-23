FROM jupyter/datascience-notebook as development


COPY . .

RUN pip install --upgrade pip \
 && pip install jason-gnss roktools pyproj Jinja2 \
 && apt-get update \
 && apt-get install -y pandoc

EXPOSE 8888/tcp

FROM development AS production

CMD ["./launch_tests.py"]

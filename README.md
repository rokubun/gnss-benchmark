# GNSS processing engine benchmarking data set

This repository contains several datasets to compute the performance of a
GNSS processing engine. This repository has been developed to help Rokubun
Jason users to assess the expected performance of the platform. However, the
orchestrator can be also used to test your own engine.

The repository includes also a tool to run the complete pipeline. To do that,
simply use these commands:

```bash
pip install gnss-benchmark
gnss_benchmark make_report
```

This tool will take a while to process (ca. 5 minutes), and after that a PDF
report should have been generated.

Note that if you do not have LaTEX installed in your system you may not be able
to generate the report in PDF. In this case, you can try other formats such as
LibreOffice ODT. To do that type

```bash
gnss_benchmark make_report --filename report.odt
```

Use the help of the tool to get more information

```bash
gnss_benchmark -h
```

## Running and developing in a container

To make sure you have all necessary components in the system, you can work
using Docker containers (recommended).

The first step would be to build the container 

```bash
docker build -t gnss-benchmark .
```

```bash
# Usage with docker run
docker run -v `pwd`:/gnss_benchmark -w /gnss_benchmark -ti gnss-benchmark bash

# Development with Jupyter
docker run --env-file .env -v `pwd`:/data -w /data -p 8888:8888 -ti gnss-benchmark jupyter notebook

# Usage with docker compose (recommended)
docker-compose -f docker-compose.yml build
docker-compose -f docker-compose.yml run gnss_benchmark bash
python setup.py install
gnss_benchmark make_report -l DEBUG
```

When using `docker-compose` remember to place your Jason credentials in an
`.env` file with these contents:

```bash
JASON_API_KEY=<api key>
JASON_SECRET_TOKEN=<your secret token>
```

Although probably not used for the end user, just for debugging purposes, 
in the event that you have a local instance of the Jason service running 
in your facilities, you can set the Jason entry point by defining the 
`JASON_API_URL` environment variable (along with its corresponding credentials).
As an example:

```bash
JASON_API_URL=http://192.168.1.54:10000/api
JASON_API_KEY=<api key>
JASON_SECRET_TOKEN=<your secret token>
```

## Using custom processing engine

By default, the tool comes bundled with [Rokubun Jason's processing engine](https://jason.rokubun.cat), but the user can specify its own processing engine. This
cannot be done with the command line tool: a custom Python code will have to
be made using the `gnss_benchmark` module. In this module, there is a package
named `jason` with an example of `processing_engine` that the user can follow
to define other processing engines.

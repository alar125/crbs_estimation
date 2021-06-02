FROM continuumio/miniconda3
COPY environment.yml /app/environment.yml
RUN conda env create -f /app/environment.yml
ENV PATH /opt/conda/envs/crbs_estimation/bin:$PATH
WORKDIR /app
CMD gunicorn -w 6 -b 0.0.0.0:$PORT -t $TIMEOUT app:app
COPY ./ /app/

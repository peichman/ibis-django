FROM python:3.11

COPY requirements.txt /opt/ibis/
WORKDIR /opt/ibis
RUN pip install -r requirements.txt
COPY . /opt/ibis/

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
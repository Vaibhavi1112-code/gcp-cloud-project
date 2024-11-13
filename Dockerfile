
FROM python:3.9-slim


WORKDIR /home/vaibhavipanchal3524/helloworld-python/app1-tutorial/


COPY . /home/vaibhavipanchal3524/helloworld-python/app1-tutorial/



RUN pip install --no-cache-dir -r requirements.txt


EXPOSE 8080


ENV PORT=8080


CMD ["python", "main.py"]

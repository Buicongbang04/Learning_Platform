FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip git curl
RUN pip3 install torch sentence-transformers fastapi uvicorn
COPY . /app
WORKDIR /app
ENV NVIDIA_DRIVER_CAPABILITIES=all
RUN pip3 install -r requirements.txt
EXPOSE 8000
CMD uvicorn main:app --host 0.0.0.0 --port 8000

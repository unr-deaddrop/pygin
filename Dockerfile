# stolen from han's dockerfile setup for the backend

FROM python:3.11.4

WORKDIR /app

# Don't use .pyc files.
ENV PYTHONDONTWRITEBYTECODE 1
# Send stdout to terminal without buffering.
ENV PYTHONUNBUFFERED 1
# Yes I'm fine with allowing unsafe pickling
ENV C_FORCE_ROOT 1

# Install Firefox (dddb)
COPY ./resources ./resources
RUN chmod +x ./resources/runtime/install-firefox.sh
RUN ./resources/runtime/install-firefox.sh

# Install Python packages
RUN pip3 install --upgrade pip
COPY requirements.txt ./
RUN pip3 install -r requirements.txt -U

# Everything else
COPY . .

# Expose ports 12345 and 12346. (plaintext_tcp, if in use)
EXPOSE 12345
EXPOSE 12346
FROM python:3.12-slim

ARG TELEGRAM_API_KEY
ENV TELEGRAM_API_KEY=${TELEGRAM_API_KEY}

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container at /usr/src/app
COPY requirements.txt requirements.txt

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the bot when the container launches
CMD ["python", "bot.py"]
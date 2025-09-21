# -- somewhere after setting WORKDIR /app and copying requirements --
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# copy the backend app files
COPY . /app

# copy our new utility script explicitly (if you prefer)
COPY fetch_and_send_twelvedata.py /app/fetch_and_send_twelvedata.py

# ensure entrypoint/cmd unchanged

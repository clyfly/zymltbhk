FROM 5hojib/aeon:dev

WORKDIR /usr/src/app
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .
CMD ["bash", "start.sh"]

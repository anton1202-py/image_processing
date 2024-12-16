FROM python:3.10

# Создаем директорию для проекта
RUN mkdir /src

RUN apt-get install -y g++
# Копируем файл зависимостей
COPY requirements.txt /src

# Устанавливаем зависимости Python
RUN pip3 install -r /src/requirements.txt --no-cache-dir

# Копируем исходный код
COPY src/ /src
COPY uwsgi.ini /src

# Устанавливаем рабочую директорию
WORKDIR /src


# Запускаем приложение
CMD ["uwsgi", "--ini", "uwsgi.ini"]

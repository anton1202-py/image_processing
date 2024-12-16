# Обработка изображений (масштабирование и поворот)

## Запуск проекта  

Клонируйте проект себе на компьютер:  
`git clone git@github.com:anton1202-py/image_processing.git`


Запустите Докер


Напишите в файле config.yaml параметры для соединения к базе данных и к rabbitmq
со следующими ключами:  

```
pg:
  host: HOST
  port: POST
  user: USERNAME
  password: PASSWORD
  database: DATABASE_NAME
  max_pool_connections: MAX_POOL_CONNECTIONS

rabbit:
  host: rabbit
  port: 5672
  user: guest
  password: guest
  routing_key: file-tasks
  queue_name: file-tasks
```

Запустите файл Makefile командой
`make`

Запустите файл docker-compose командой
`docker-compose up`


Кратко о функция:  
1. Сервис создает задачи на обработку изображения.  
POST: `api/processing/<int:file_id>`
`
{
    "scale": int (процент масштабирования),
    "angle_rotate": int (угол поворота изображения)
}
`
Response:  
`
{
  "created_at": str (дата создания задачи),
  "file_id": int (id файла для обработки),
  "processed_file_id": int(id нового файла, который создался после обработки),
  "processing_parameters": {
      "scale": int (процент масштабирования),
      "angle_rotate": int (угол поворота изображения)
  },
  "status": str (текущий статус выполнения задачи),
  "task_id": int (id созданной задачи),
  "updated_at": str (дата обнвления данных задачи)
}
`
2. Показывает статус выполнения задачи:
GET: `api/tasks/<int:task_id>`

3. Показывает список всех задач.
GET: `api/tasks`

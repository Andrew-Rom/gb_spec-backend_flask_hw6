# Необходимо создать базу данных для интернет-магазина.
# База данных должна состоять из трёх таблиц: товары, заказы и пользователи.
#
# — Таблица «Товары» должна содержать информацию о доступных товарах, их описаниях и ценах.
# — Таблица «Заказы» должна содержать информацию о заказах, сделанных пользователями.
# — Таблица «Пользователи» должна содержать информацию о зарегистрированных пользователях магазина.
#
# • Таблица пользователей должна содержать следующие поля:
#       id (PRIMARY KEY),
#       имя,
#       фамилия,
#       адрес электронной почты и
#       пароль.
#
# • Таблица заказов должна содержать следующие поля:
#       id (PRIMARY KEY),
#       id пользователя (FOREIGN KEY),
#       id товара (FOREIGN KEY),
#       дата заказа и
#       статус заказа.
#
# • Таблица товаров должна содержать следующие поля:
#       id (PRIMARY KEY),
#       название,
#       описание и
#       цена.
#
# Создайте модели pydantic для получения новых данных и возврата существующих в БД для каждой из трёх таблиц.
# Реализуйте CRUD операции для каждой из таблиц через создание маршрутов, REST API.
import random
from datetime import date
from typing import List

import databases
import sqlalchemy
from fastapi import FastAPI, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import ForeignKey
from starlette.responses import JSONResponse

DATABASE_URL = "sqlite:///mydatabase.db"
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

users = sqlalchemy.Table(
    "users",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("first_name", sqlalchemy.String(64)),
    sqlalchemy.Column("last_name", sqlalchemy.String(128)),
    sqlalchemy.Column("email", sqlalchemy.String(128)),
    sqlalchemy.Column("password", sqlalchemy.String(16)),
)

orders = sqlalchemy.Table(
    "orders",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("user_id", sqlalchemy.Integer, ForeignKey("users.id")),
    sqlalchemy.Column("product_id", sqlalchemy.Integer, ForeignKey("products.id")),
    sqlalchemy.Column("created_at", sqlalchemy.Date),
    sqlalchemy.Column("status", sqlalchemy.String(32)),
)

products = sqlalchemy.Table(
    "products",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("title", sqlalchemy.String(64)),
    sqlalchemy.Column("description", sqlalchemy.String(256)),
    sqlalchemy.Column("price", sqlalchemy.Float),
)

engine = sqlalchemy.create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
metadata.create_all(engine)

app = FastAPI()


class UserIn(BaseModel):
    first_name: str = Field(..., max_length=64)
    last_name: str = Field(..., max_length=128)
    email: str = Field(..., pattern="[a-zA-z0-9]+@[a-zA-z0-9]+[.]([a-zA-z0-9]{2,4})", max_length=128)
    password: str = Field(..., min_length=3, max_length=16)


class User(BaseModel):
    id: int
    first_name: str = Field(..., max_length=64)
    last_name: str = Field(..., max_length=128)
    email: str = Field(..., pattern="[a-zA-z0-9]+@[a-zA-z0-9]+[.]([a-zA-z0-9]{2,4})", max_length=128)
    password: str = Field(..., min_length=3, max_length=16)


class OrderIn(BaseModel):
    user_id: int
    product_id: int
    created_at: date = Field(default=date.today())
    status: str = Field(..., max_length=32)


class Order(BaseModel):
    id: int
    user_id: int
    product_id: int
    created_at: date
    status: str = Field(..., max_length=32)


class ProductIn(BaseModel):
    title: str = Field(..., max_length=64)
    description: str = Field(default=None, max_length=256)
    price: float = Field(..., lt=0.0)


class Product(BaseModel):
    id: int
    title: str = Field(..., max_length=64)
    description: str = Field(default=None, max_length=256)
    price: float = Field(..., lt=0.0)


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.get("/users/", response_model=List[User])
async def get_all_users(skip: int = Query(default=0, ge=0), limit: int = Query(default=15, ge=1)):
    query = users.select()
    lst_users = await database.fetch_all(query)
    return lst_users[skip: skip + limit]


@app.post("/users/", response_model=User)
async def add_user(user: UserIn):
    query = users.insert().values(**user.dict())
    last_record_id = await database.execute(query)
    return {**user.dict(), "id": last_record_id}


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int = Path(..., ge=1)):
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    return user if user else JSONResponse(content=f'User with ID {user_id} not found', status_code=404)


@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, new_user: UserIn):
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if user:
        query = users.update().where(users.c.id == user_id).values(**new_user.dict())
        await database.execute(query)
        return {**new_user.dict(), "id": user_id}
    return JSONResponse(content=f'User with ID {user_id} not found', status_code=404)


@app.delete("/users/{user_id}")
async def delete_user(user_id: int = Path(..., ge=1)):
    user = await database.fetch_one(users.select().where(users.c.id == user_id))
    if user:
        query = users.delete().where(users.c.id == user_id)
        await database.execute(query)
        return {"message": "User deleted"}
    return JSONResponse(content=f'User with ID {user_id} not found', status_code=404)


@app.get("/products/", response_model=List[Product])
async def get_all_products(skip: int = Query(default=0, ge=0), limit: int = Query(default=15, ge=1)):
    query = products.select()
    lst_products = await database.fetch_all(query)
    return lst_products[skip: skip + limit]


@app.post("/products/", response_model=Product)
async def add_product(product: ProductIn):
    query = products.insert().values(**product.dict())
    last_record_id = await database.execute(query)
    return {**product.dict(), "id": last_record_id}


@app.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    product = await database.fetch_one(users.select().where(products.c.id == product_id))
    return product if product else JSONResponse(content=f'Product with ID {product_id} not found', status_code=404)


@app.put("/products/{product_id}", response_model=Product)
async def update_product(product_id: int, new_product: ProductIn):
    product = await database.fetch_one(users.select().where(products.c.id == product_id))
    if product:
        query = products.update().where(products.c.id == product_id).values(**new_product.dict())
        await database.execute(query)
        return {**new_product.dict(), "id": product_id}
    return JSONResponse(content=f'Product with ID {product_id} not found', status_code=404)


@app.delete("/products/{product_id}")
async def delete_product(product_id: int = Path(..., ge=1)):
    product = await database.fetch_one(products.select().where(products.c.id == product_id))
    if product:
        query = products.delete().where(products.c.id == product_id)
        await database.execute(query)
        return {"message": "Product deleted"}
    return JSONResponse(content=f'Product with ID {product_id} not found', status_code=404)


@app.get("/orders/", response_model=List[Order])
async def get_all_orders(skip: int = Query(default=0, ge=0), limit: int = Query(default=15, ge=1)):
    query = orders.select()
    lst_orders = await database.fetch_all(query)
    return lst_orders[skip: skip + limit]


@app.post("/orders/", response_model=Order)
async def add_order(order: OrderIn):
    query = orders.insert().values(**order.dict())
    last_record_id = await database.execute(query)
    return {**order.dict(), "id": last_record_id}


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    order = await database.fetch_one(orders.select().where(orders.c.id == order_id))
    return order if order else JSONResponse(content=f'Order with ID {order_id} not found', status_code=404)


@app.put("/orders/{order_id}", response_model=Order)
async def update_order(order_id: int, new_order: OrderIn):
    order = await database.fetch_one(orders.select().where(orders.c.id == order_id))
    if order:
        query = orders.update().where(orders.c.id == order_id).values(**new_order.dict())
        await database.execute(query)
        return {**new_order.dict(), "id": order_id}
    return JSONResponse(content=f'Order with ID {order_id} not found', status_code=404)


@app.delete("/orders/{order_id}")
async def delete_order(order_id: int = Path(..., ge=1)):
    order = await database.fetch_one(orders.select().where(orders.c.id == order_id))
    if order:
        query = orders.delete().where(orders.c.id == order_id)
        await database.execute(query)
        return {"message": "Order deleted"}
    return JSONResponse(content=f'Order with ID {order_id} not found', status_code=404)


FIRST_NAMES = ['John', 'Bob', 'Kate', 'Ann', 'Patric', 'Sid', 'Iren',
               'Henry', 'Elona', 'Linda', 'Nick', 'Rick', 'Tom', 'Jane']
LAST_NAMES = ['Doe', 'Black', 'White', 'Mask', 'Bess', 'Lee', 'Russo', 'Prost', 'Senna', 'Miles']
EMAILS = ['mail', 'gmail', 'yandex', 'yahoo', 'outlook', 'rambler']
DOMAINS = ['.com', '.ru', '.net', '.vn', '.fr', '.uk', '.hz']


@app.get("/fake_users/{count}")
async def create_fake_users(count: int):
    for i in range(count):
        user_name = random.choice(FIRST_NAMES)
        user_surname = random.choice(LAST_NAMES)
        user_email = f'{user_name[0].lower()}_{user_surname.lower()}@' \
                     + random.choice(EMAILS) \
                     + random.choice(DOMAINS)
        query = users.insert().values(first_name=user_name,
                                      last_name=user_surname,
                                      email=user_email,
                                      password=user_surname + str(i))
        await database.execute(query)
    return {'message': f'{count} fake users create'}


@app.get("/fake_products/{count}")
async def create_fake_products(count: int):
    for i in range(count):
        title = random.choice([f'laptop{i}', f'keyboard{i}', f'mouse{i}', f'smartphone{i}', f'tv{i}'])
        description = random.choice(['black', 'grey', 'white', 'red', 'silver'])
        price = random.choice([20.55, 10.33, 123.10])
        query = products.insert().values(title=title, description=description, price=price)
        await database.execute(query)
    return {'message': f'{count} fake products created'}


@app.get("/fake_orders/{count}")
async def create_fake_orders(count: int = 3):
    lst_users = await database.fetch_all(users.select(users.c.id))
    lst_products = await database.fetch_all(products.select(products.c.id))
    if len(lst_users) and len(lst_products):
        lst_user_id = [item[0] for item in lst_users]
        lst_product_id = [item[0] for item in lst_users]
        for i in range(count):
            user_id = random.choice(lst_user_id)
            product_id = random.choice(lst_product_id)
            order_date = date.today()
            status = random.choice(['created', 'paid', 'canceled', 'delivered'])
            query = orders.insert().values(user_id=user_id, product_id=product_id, created_at=order_date, status=status)
            await database.execute(query)
        return {'message': f'{count} fake orders created'}
    return {'message': 'No one fake order was created'}

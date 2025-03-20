

import sqlalchemy as sa

engine = sa.create_engine("sqlite:///:memory:")
connection = engine.connect()

metadata = sa.MetaData()

order_table = sa.Table(
    "orders",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("product", sa.String),
    sa.Column("quantity", sa.Integer),
)


def insert_order(product: str, quantity: int) -> None:
    query = order_table.insert().values(product=product, quantity=quantity)
    connection.execute(query)


def select_order(id: int) -> sa.engine.Result:
    query = order_table.select().where(order_table.c.id == id)
    result = connection.execute(query)
    return result.fetchone()


def main() -> None:
    metadata.create_all(engine)
    insert_order("Coca-cola", 3)
    print(select_order("1"))
    connection.close()


if __name__ == "__main__":
    main()

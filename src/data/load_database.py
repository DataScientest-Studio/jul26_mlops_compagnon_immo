
import os
import pandas as pd

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

load_dotenv()

# 1. Vérifier et créer la base PostgreSQL
def creer_base():
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "DATABASE_URL absent : configurer le fichier .env"
        )

    db_url = make_url(url)
    nom_base = db_url.database

    if not nom_base:
        raise RuntimeError("Nom de la base absent dans DATABASE_URL")

    # Connexion à la base système postgres
    admin_url = db_url.set(database="postgres")

    engine = create_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
        pool_pre_ping=True
    )

    try:
        with engine.connect() as connexion:
            existe = connexion.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :nom"),
                {"nom": nom_base}
            ).scalar()

            if not existe:
                nom_sql = engine.dialect.identifier_preparer.quote(nom_base)
                connexion.execute(
                    text(f"CREATE DATABASE {nom_sql}")
                )
                print(f"Base PostgreSQL '{nom_base}' créée")
            else:
                print(f"Base PostgreSQL '{nom_base}' déjà existante")
    finally:
        engine.dispose()


# 2. Charger les données dans PostgreSQL
def charger(df: pd.DataFrame) -> None:
    url = os.getenv("DATABASE_URL")

    if not url:
        raise RuntimeError("DATABASE_URL absent dans .env")

    engine = create_engine(url, pool_pre_ping=True)

    try:
        with engine.begin() as connexion:
            df.to_sql(
                "transactions_immobilieres",
                con=connexion,
                schema="public",
                if_exists="replace",
                index=False,
                chunksize=1000,
                method="multi"
            )

            count = connexion.execute(
                text(
                    "SELECT COUNT(*) "
                    "FROM public.transactions_immobilieres"
                )
            ).scalar_one()

        if count != len(df):
            raise RuntimeError(
                f"Nombre de lignes inattendu : {count} / {len(df)}"
            )

        print(
            f"PostgreSQL : {count:,} lignes "
            "dans transactions_immobilieres"
        )
    finally:
        engine.dispose()


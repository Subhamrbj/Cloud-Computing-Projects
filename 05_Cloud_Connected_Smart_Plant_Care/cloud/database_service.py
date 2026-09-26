import os
import re
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL', 'sqlite:///./plantcare.db')
if url.startswith('postgresql://'):
    url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql+psycopg://', 1)
engine = create_engine(url, pool_pre_ping=True, connect_args={'check_same_thread': False, 'timeout': 30} if url.startswith('sqlite') else {})
Session = sessionmaker(engine, expire_on_commit=False)
schema = os.getenv('DATABASE_SCHEMA','plantcare') if engine.dialect.name == 'postgresql' else None
if schema and not re.fullmatch(r'[a-z][a-z0-9_]{0,30}',schema):
    raise RuntimeError('DATABASE_SCHEMA must be a simple lowercase SQL identifier')
class Base(DeclarativeBase):
    metadata = MetaData(schema=schema)

def initialize_database():
    # PostgreSQL keeps application data outside Supabase's default exposed public schema.
    if schema:
        with engine.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    Base.metadata.create_all(engine)

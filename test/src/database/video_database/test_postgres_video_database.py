from src.database.videos.postgres_video_database import PostgresVideoDatabase
from src.database.videos.video_database import VideoData
import datetime
import pytest
import psycopg2
from typing import NamedTuple
import requests
import os
from io import BytesIO

class FakePostgres(NamedTuple):
    closed: int

fake_video_data = VideoData(title="Titulo", description="Descripcion",
                            creation_time=datetime.datetime.now(), visible=True,
                            location="Buenos Aires", file_location="file_location")

fake_video_data2 = VideoData(title="Titulo2", description="Descripcion",
                             creation_time=datetime.datetime.now()+datetime.timedelta(days=1), visible=True,
                             location="Buenos Aires", file_location="file_location")

@pytest.fixture(scope="function")
def video_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "dummy"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    database = PostgresVideoDatabase(*(["DUMB_ENV_NAME"]*5))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/video_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.videos_table_name = "chotuve.videos"
    return database

def test_postgres_connection_error(monkeypatch, video_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresVideoDatabase(*(["DUMB_ENV_NAME"] * 5))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)

def test_add_video_and_query(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0].title == "Titulo"

def test_add_two_videos_and_query(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data2)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 2
    assert videos[0].title == "Titulo2"
    assert videos[1].title == "Titulo"

def test_add_two_videos_and_get_top(monkeypatch, video_postgres_database):
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 0
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    videos = video_postgres_database.list_top_videos()
    assert len(videos) == 1
    assert videos[0][0] == "giancafferata@hotmail.com"
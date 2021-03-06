from src.database.videos.postgres_video_database import PostgresVideoDatabase
from src.database.videos.exceptions.no_more_videos_error import NoMoreVideosError
from src.database.videos.video_database import VideoData, Reaction
import datetime
import pytest
import psycopg2
from typing import NamedTuple
import requests
import os
from io import BytesIO
from src.database.utils.postgres_connection import PostgresUtils
import time


class FakePostgres(NamedTuple):
    closed: int


fake_video_data = VideoData(title="Titulo", description="Descripcion coso",
                            creation_time=datetime.datetime.now(), visible=True,
                            location="Buenos Aires", file_location="file_location")

fake_video_data2 = VideoData(title="Titulo2", description="Descripcion2 coso",
                             creation_time=datetime.datetime.now() + datetime.timedelta(days=1), visible=True,
                             location="Buenos Aires", file_location="file_location")


@pytest.fixture(scope="function")
def video_postgres_database(monkeypatch, postgresql):
    os.environ["DUMB_ENV_NAME"] = "dummy"
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(0))
    monkeypatch.setattr(PostgresUtils, "get_postgres_connection",
                        lambda *args, **kwargs: psycopg2.connect(*args, **kwargs))
    database = PostgresVideoDatabase(*(["DUMB_ENV_NAME"] * 8))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)
    with open("test/src/database/video_database/config/initialize_db.sql", "r") as initialize_query:
        cursor = postgresql.cursor()
        cursor.execute(initialize_query.read())
        postgresql.commit()
        cursor.close()
    database.conn = postgresql
    database.videos_table_name = "chotuve.videos"
    database.users_table_name = "chotuve.users"
    database.video_reactions_table_name = "chotuve.video_reactions"
    database.video_comments_table_name = "chotuve.video_comments"
    yield database
    postgresql.close()


def test_postgres_connection_error(monkeypatch, video_postgres_database):
    aux_connect = psycopg2.connect
    monkeypatch.setattr(psycopg2, "connect", lambda *args, **kwargs: FakePostgres(1))
    with pytest.raises(ConnectionError):
        database = PostgresVideoDatabase(*(["DUMB_ENV_NAME"] * 8))
    monkeypatch.setattr(psycopg2, "connect", aux_connect)


def test_add_video_and_query(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0][0].title == "Titulo"


def test_add_two_videos_and_query(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data2)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 2
    assert videos[0][0].title == "Titulo2"
    assert videos[1][0].title == "Titulo"


def test_delete_videos_and_query(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data2)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 2
    video_postgres_database.delete_video("giancafferata@hotmail.com", fake_video_data.title)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0][0].title == fake_video_data2.title


def test_add_video_and_get_top(monkeypatch, video_postgres_database):
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 0
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    videos = video_postgres_database.list_top_videos()
    assert len(videos) == 1
    assert videos[0][0]["email"] == "giancafferata@hotmail.com"


def test_add_two_videos_and_search(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data2)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 2
    assert len(video_postgres_database.search_videos("titulo")) == 1
    assert len(video_postgres_database.search_videos("Titulo")) == 1
    assert len(video_postgres_database.search_videos("titulo2")) == 1
    assert len(video_postgres_database.search_videos("Titulo2")) == 1
    assert len(video_postgres_database.search_videos("descripcion")) == 1
    assert len(video_postgres_database.search_videos("descripcion2")) == 1
    assert len(video_postgres_database.search_videos("coso")) == 2
    search_result = video_postgres_database.search_videos("coso titulo")
    assert len(search_result) == 2
    assert search_result[0][1].title == "Titulo"


def test_react_video(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0][1][Reaction.like] == 0
    assert videos[0][1][Reaction.dislike] == 0

    reaction = video_postgres_database.get_video_reaction('cafferatagian@hotmail.com',
                                                          'giancafferata@hotmail.com', 'Titulo')
    assert not reaction

    video_postgres_database.react_video('cafferatagian@hotmail.com', 'giancafferata@hotmail.com',
                                        'Titulo', Reaction.like)

    reaction = video_postgres_database.get_video_reaction('cafferatagian@hotmail.com',
                                                          'giancafferata@hotmail.com', 'Titulo')
    assert reaction.name == "like"

    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0][1][Reaction.like] == 1
    assert videos[0][1][Reaction.dislike] == 0
    video_postgres_database.react_video('cafferatagian@hotmail.com', 'giancafferata@hotmail.com',
                                        'Titulo', Reaction.dislike)
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0][1][Reaction.like] == 0
    assert videos[0][1][Reaction.dislike] == 1
    video_postgres_database.delete_reaction('cafferatagian@hotmail.com',
                                            'giancafferata@hotmail.com',
                                            'Titulo')
    videos = video_postgres_database.list_user_videos("giancafferata@hotmail.com")
    assert len(videos) == 1
    assert videos[0][1][Reaction.like] == 0
    assert videos[0][1][Reaction.dislike] == 0


def test_comment_video_and_query(monkeypatch, video_postgres_database):
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data2)
    video_postgres_database.comment_video('cafferatagian@hotmail.com', 'giancafferata@hotmail.com',
                                          fake_video_data.title, "Comentario 1")
    video_postgres_database.comment_video('asd@asd.com', 'giancafferata@hotmail.com',
                                          fake_video_data2.title, "Comentario 2")
    video_postgres_database.comment_video('asd@asd.com', 'giancafferata@hotmail.com',
                                          fake_video_data.title, "Comentario 3")
    users1, comments1 = video_postgres_database.get_comments('giancafferata@hotmail.com',
                                                             fake_video_data.title)
    assert len(users1) == 2
    assert users1[0]["email"] == 'asd@asd.com'
    assert users1[1]["email"] == 'cafferatagian@hotmail.com'
    assert comments1[0].content == "Comentario 3"
    assert comments1[1].content == "Comentario 1"
    users2, comments2 = video_postgres_database.get_comments('giancafferata@hotmail.com',
                                                             fake_video_data2.title)
    assert len(users2) == 1
    assert users2[0]["email"] == 'asd@asd.com'
    assert comments2[0].content == "Comentario 2"


def test_add_videos_and_get_paginated(monkeypatch, video_postgres_database):
    page_empty = video_postgres_database.get_paginated_videos(page=0, per_page=1)
    assert page_empty[1] == 0
    with pytest.raises(NoMoreVideosError):
        video_postgres_database.get_paginated_videos(page=1, per_page=1)

    fake_video_data = VideoData(title="Titulo", description="Descripcion coso",
                                creation_time=datetime.datetime.now(), visible=True,
                                location="Buenos Aires", file_location="file_location")
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)

    fake_video_data = VideoData(title="Titulo2", description="Descripcion coso",
                                creation_time=datetime.datetime.now(), visible=True,
                                location="Buenos Aires", file_location="file_location")
    video_postgres_database.add_video("asd@asd.com", fake_video_data)

    fake_video_data = VideoData(title="Titulo2", description="Descripcion coso",
                                creation_time=datetime.datetime.now(), visible=True,
                                location="Buenos Aires", file_location="file_location")
    video_postgres_database.add_video("giancafferata@hotmail.com", fake_video_data)

    page1 = video_postgres_database.get_paginated_videos(page=0, per_page=2)
    page2 = video_postgres_database.get_paginated_videos(page=1, per_page=2)
    assert page1[1] == 2
    assert page2[1] == 2
    assert len(page1[0]) == 2
    assert len(page2[0]) == 1
    assert page1[0][0][0]["email"] == "giancafferata@hotmail.com"
    assert page1[0][1][0]["email"] == "asd@asd.com"
    assert page2[0][0][0]["email"] == "giancafferata@hotmail.com"
    assert page1[0][0][1].title == "Titulo2"
    assert page1[0][1][1].title == "Titulo2"
    assert page2[0][0][1].title == "Titulo"
    with pytest.raises(NoMoreVideosError):
        video_postgres_database.get_paginated_videos(page=2, per_page=2)

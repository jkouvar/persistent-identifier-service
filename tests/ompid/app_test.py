import json

from pytest_postgresql.compat import connection, cursor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.testclient import TestClient

import ompid
import ompid.db
from ompid import app, Base


def _init_test_client(postgresql: connection) -> TestClient:
    mock_engine = create_engine(
        name_or_url='postgresql://',
        connect_args=postgresql.get_dsn_parameters())

    async def get_mock_db():
        MockSessionLocal = \
            sessionmaker(autocommit=False, autoflush=False, bind=mock_engine)
        db = MockSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[ompid.get_db] = get_mock_db
    Base.metadata.create_all(mock_engine)

    return TestClient(app)


def test_users_register(postgresql: connection):
    client = _init_test_client(postgresql)

    # normal user -----------------------------------------
    user_name = 'User ABC'
    user_namespace = 'abc'
    response = client.post(
        '/users/register',
        json={'name': user_name, 'user_namespace': user_namespace})

    # no errors were raised
    assert response.status_code == 200

    # user data can be found in the database
    user_id: int = json.loads(response.content)['id']
    cur: cursor = postgresql.cursor()
    cur.execute(
        f'SELECT * FROM topio_user '
        f'WHERE id=%s AND name=%s AND user_namespace=%s;',
        (user_id, user_name, user_namespace))
    results = cur.fetchall()
    cur.close()
    assert len(results) == 1

    # user with broken namespace (contains whitespace) ----
    user_name = 'User DEF'
    user_namespace = 'this is broken'
    response = client.post(
        '/users/register',
        json={'name': user_name, 'user_namespace': user_namespace})

    # should cause a client error 422 (Unprocessable Entity)...
    assert response.status_code == 422

    # ...and it should be a value error
    error_type = json.loads(response.content)['detail'][0]['type']
    assert error_type == 'value_error'

    # ...and no DB write should have happened
    cur: cursor = postgresql.cursor()
    cur.execute(
        f'SELECT * FROM topio_user '
        f'WHERE id=%s AND name=%s AND user_namespace=%s;',
        (user_id, user_name, user_namespace))
    results = cur.fetchall()
    cur.close()
    assert len(results) == 0


def test_users_info(postgresql: connection):
    client = _init_test_client(postgresql)

    user_name = 'User ABC'
    user_namespace = 'abc'
    response = client.post(
        '/users/register',
        json={'name': user_name, 'user_namespace': user_namespace})
    user_id: int = json.loads(response.content)['id']

    response = client.get(
        f'/users/{user_id}',
        json={'topio_user_id': user_id})

    assert response.status_code == 200

    # {"name":"User ABC","user_namespace":"abc","id":1}
    user_info_data = json.loads(response.content)

    assert user_info_data['name'] == user_name
    assert user_info_data['user_namespace'] == user_namespace
    assert user_info_data['id'] == user_id


def test_asset_types_register(postgresql: connection):
    client = _init_test_client(postgresql)

    # normal asset type registration
    asset_type_id = 'file'
    asset_type_description = 'Data assets provided as downloadable file'

    response = client.post(
        '/asset_types/register',
        json={'id': asset_type_id, 'description': asset_type_description}
    )

    assert response.status_code == 200

    cur: cursor = postgresql.cursor()
    cur.execute(
        f'SELECT * FROM topio_asset_type WHERE id=%s;',
        (asset_type_id,))
    results = cur.fetchall()
    cur.close()
    assert len(results) == 1
    assert results[0][1] == asset_type_description

    # registration of asset type with broken asset type ID (contains spaces)
    asset_type_id = 'this is broken'
    asset_type_description = \
        'This is a broken asset type with spaces in its identifier string'

    response = client.post(
        '/asset_types/register',
        json={'id': asset_type_id, 'description': asset_type_description}
    )

    assert response.status_code == 422

    cur: cursor = postgresql.cursor()
    cur.execute(
        f'SELECT * FROM topio_asset_type WHERE id=%s;',
        (asset_type_id,))
    results = cur.fetchall()
    cur.close()
    assert len(results) == 0


def test_asset_types_info(postgresql: connection):
    client = _init_test_client(postgresql)

    asset_type_id = 'file'
    asset_type_description = 'Data assets provided as downloadable file'

    client.post(
        '/asset_types/register',
        json={'id': asset_type_id, 'description': asset_type_description}
    )

    response = client.get(
        f'/asset_types/{asset_type_id}',
        json={'id': asset_type_id}
    )

    assert response.status_code == 200

    asset_info_data = json.loads(response.content)

    assert asset_info_data['id'] == asset_type_id
    assert asset_info_data['description'] == asset_type_description

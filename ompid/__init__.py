import os
from typing import List

import yaml
from fastapi import FastAPI, Response, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ompid.models import Base, TopioUser, TopioUserCreate, TopioUserORM, \
    TopioAssetType, TopioAssetTypeORM, TopioAsset, TopioAssetORM, \
    TopioAssetCreate, TopioUserQuery


def load_default_configuration():
    with open(os.path.join(os.getcwd(), 'settings.yml')) as yaml_file:
        cfg = yaml.safe_load(yaml_file)

    return cfg


async def get_db():
    from ompid.db import SessionLocal
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()

app = FastAPI()


@app.on_event('startup')
def init_tables():
    import ompid.db
    Base.metadata.create_all(ompid.db.engine)


@app.post('/users/register', response_model=TopioUser, responses={201: {"model": TopioUser}})
async def register_user(topio_user: TopioUserCreate, db: Session = Depends(get_db)):

    topio_user_orm = (
        db
        .query(TopioUserORM)
        .filter(and_(TopioUserORM.name == topio_user.name, TopioUserORM.user_namespace == topio_user.user_namespace))
        .first()
    )

    if not topio_user_orm is None:
        return topio_user_orm

    topio_user_orm = TopioUserORM(
        name=topio_user.name, user_namespace=topio_user.user_namespace)

    db.add(topio_user_orm)
    db.commit()
    db.refresh(topio_user_orm)

    topio_user_json = jsonable_encoder(topio_user_orm)
    return JSONResponse(status_code=201, content=topio_user_json)


@app.get('/users/{topio_user_id}', response_model=TopioUser)
async def get_user_info(topio_user_id: int, db: Session = Depends(get_db)):
    topio_user_orm = \
        db.query(TopioUserORM).filter(TopioUserORM.id == topio_user_id).first()

    return topio_user_orm


@app.post('/asset_types/register', response_model=TopioAssetType, responses={201: {"model": TopioAssetType}})
async def register_asset_type(
        topio_asset_type: TopioAssetType, db: Session = Depends(get_db)):

    topio_asset_type_orm = (
        db
        .query(TopioAssetTypeORM)
        .filter(and_(TopioAssetTypeORM.id == topio_asset_type.id, TopioAssetTypeORM.description == topio_asset_type.description))
        .first()
    )

    if not topio_asset_type_orm is None:
        return topio_asset_type_orm

    topio_asset_type_orm = TopioAssetTypeORM(
        id=topio_asset_type.id, description=topio_asset_type.description)

    db.add(topio_asset_type_orm)
    db.commit()
    db.refresh(topio_asset_type_orm)

    topio_asset_type_json = jsonable_encoder(topio_asset_type_orm)
    return JSONResponse(status_code=201, content=topio_asset_type_json)


@app.get('/asset_types/{topio_asset_type_id}', response_model=TopioAssetType)
async def get_asset_namespace_info(
        topio_asset_type_id: str, db: Session = Depends(get_db)):

    topio_asset_type_orm = db\
        .query(TopioAssetTypeORM)\
        .filter(TopioAssetTypeORM.id == topio_asset_type_id)\
        .first()

    return topio_asset_type_orm


@app.get('/asset_types/', response_model=List[TopioAssetType])
async def get_asset_types(db: Session = Depends(get_db)):
    return db.query(TopioAssetTypeORM).all()


@app.post('/assets/register', response_model=TopioAsset)
async def register_asset(topio_asset: TopioAssetCreate, db: Session = Depends(get_db)):
    topio_asset_orm = TopioAssetORM(
        local_id=topio_asset.local_id,
        owner_id=topio_asset.owner_id,
        asset_type=topio_asset.asset_type,
        description=topio_asset.description)

    db.add(topio_asset_orm)
    db.commit()
    db.refresh(topio_asset_orm)

    return topio_asset_orm


@app.get('/assets/topio_id', response_model=str, responses={404: {"model": str}})
async def get_topio_id(
        owner_id: int,
        asset_type: str, 
        local_id: str,
        db: Session = Depends(get_db)):
    """
    Returns the topio ID for a given asset identified by
    - the asset owner ID
    - the asset type
    - the asset's local ID (e.g. hdfs://foo/bar, postgresql://user:pw@dbhost/db)

    :param owner_id: the asset owner ID
    :param asset_type: the asset type
    :param local_id: the asset's local ID
    :param db: database session (will be provided by FastAPI's dependency
        injection mechanism.
    :return: A string containing the topio ID of the respective asset
    """

    asset = db\
        .query(TopioAssetORM)\
        .filter(TopioAssetORM.owner_id == owner_id,
                TopioAssetORM.asset_type == asset_type,
                TopioAssetORM.local_id == local_id)\
        .first()

    if asset is None:
        return Response(status_code=404, content='No topio ID found for the given parameters')

    return asset.topio_id


@app.get('/assets/custom_id', response_model=str)
async def get_custom_id(query: dict, db: Session = Depends(get_db)):
    topio_id: str = query.get('topio_id')

    if topio_id is None:
        asset = None
    else:
        asset = db\
            .query(TopioAssetORM)\
            .filter(
                TopioAssetORM.topio_id == topio_id,
                TopioAssetORM.local_id != None)\
            .first()

    if asset is None:
        raise HTTPException(
            404,
            f'No custom ID found for topio ID {topio_id}')

    return asset.local_id


@app.get('/assets/', response_model=List[TopioAsset])
async def get_users_assets(user: TopioUserQuery, db: Session = Depends(get_db)):
    return db\
        .query(TopioAssetORM)\
        .filter(TopioAssetORM.owner_id == user.user_id)\
        .all()

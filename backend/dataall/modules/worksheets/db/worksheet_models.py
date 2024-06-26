import datetime
import enum

from sqlalchemy import Column, DateTime, Integer, Enum, String
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import query_expression

from dataall.base.db import Base
from dataall.base.db import Resource, utils


class QueryType(enum.Enum):
    chart = 'chart'
    data = 'data'


class Worksheet(Resource, Base):
    __tablename__ = 'worksheet'
    worksheetUri = Column(String, primary_key=True, default=utils.uuid('_'))
    SamlAdminGroupName = Column(String, nullable=False)
    sqlBody = Column(String, nullable=True)
    chartConfig = Column(postgresql.JSON, nullable=True)
    userRoleForWorksheet = query_expression()
    lastSavedAthenaQueryIdForQuery = Column(String, nullable=True)
    lastSavedAthenaQueryIdForChart = Column(String, nullable=True)


class WorksheetQueryResult(Base):
    __tablename__ = 'worksheet_query_result'
    worksheetUri = Column(String, nullable=False)
    AthenaQueryId = Column(String, primary_key=True)
    status = Column(String, nullable=False)
    queryType = Column(Enum(QueryType), nullable=False, default=True)
    sqlBody = Column(String, nullable=False)
    AwsAccountId = Column(String, nullable=False)
    region = Column(String, nullable=False)
    OutputLocation = Column(String, nullable=False)
    error = Column(String, nullable=True)
    ElapsedTimeInMs = Column(Integer, nullable=True)
    DataScannedInBytes = Column(Integer, nullable=True)
    created = Column(DateTime, default=datetime.datetime.now)

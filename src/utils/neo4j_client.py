"""Neo4j 데이터베이스 클라이언트"""

from contextlib import asynccontextmanager
from neo4j import AsyncGraphDatabase, AsyncDriver
from config.settings import get_settings


class Neo4jClient:
    """Neo4j 비동기 클라이언트"""

    def __init__(self):
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await self._driver.verify_connectivity()

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j client not connected. Call connect() first.")
        return self._driver

    async def execute_query(
        self,
        query: str,
        parameters: dict | None = None,
        database: str = "neo4j",
    ) -> list[dict]:
        """Cypher 쿼리 실행"""
        async with self.driver.session(database=database) as session:
            result = await session.run(query, parameters or {})
            records = await result.data()
            return records

    async def execute_write(
        self,
        query: str,
        parameters: dict | None = None,
        database: str = "neo4j",
    ) -> None:
        """쓰기 쿼리 실행"""
        async with self.driver.session(database=database) as session:
            await session.run(query, parameters or {})


@asynccontextmanager
async def get_neo4j_client():
    """Neo4j 클라이언트 컨텍스트 매니저"""
    client = Neo4jClient()
    try:
        await client.connect()
        yield client
    finally:
        await client.close()

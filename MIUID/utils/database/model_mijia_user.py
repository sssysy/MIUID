"""米家用户绑定与登录凭据表。"""

from typing import TypeVar

from sqlalchemy import UniqueConstraint, delete
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, col, select

from gsuid_core.utils.database.base_models import BaseIDModel, with_read_session, with_session

T_MijiaUser = TypeVar("T_MijiaUser", bound="MijiaUser")


class MijiaUser(BaseIDModel, table=True):
    """机器人用户与米家账号的一对一绑定。"""

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_mijiauser_user_id"),
        {"extend_existing": True},
    )

    user_id: str = Field(title="机器人用户ID")
    mijia_user_id: str = Field(default="", index=True, title="米家用户ID")
    auth_json: str = Field(default="", title="米家登录凭据JSON")

    @classmethod
    @with_read_session
    async def get_by_user_id(
        cls: type[T_MijiaUser],
        session: AsyncSession,
        user_id: str,
    ) -> T_MijiaUser | None:
        result = await session.execute(select(cls).where(col(cls.user_id) == user_id))
        return result.scalars().first()

    @classmethod
    @with_session
    async def save_auth(
        cls: type[T_MijiaUser],
        session: AsyncSession,
        user_id: str,
        mijia_user_id: str,
        auth_json: str,
    ) -> None:
        result = await session.execute(select(cls).where(col(cls.user_id) == user_id))
        row = result.scalars().first()
        if row is None:
            session.add(
                cls(
                    user_id=user_id,
                    mijia_user_id=mijia_user_id,
                    auth_json=auth_json,
                )
            )
            return

        row.mijia_user_id = mijia_user_id
        row.auth_json = auth_json
        session.add(row)

    @classmethod
    @with_session
    async def delete_by_user_id(
        cls: type[T_MijiaUser],
        session: AsyncSession,
        user_id: str,
    ) -> int:
        result = await session.execute(delete(cls).where(col(cls.user_id) == user_id))
        return result.rowcount if isinstance(result, CursorResult) else 0

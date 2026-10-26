"""米家用户绑定与登录凭据表。"""

from typing import TypeVar

from sqlalchemy import UniqueConstraint, delete, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, col, select

from gsuid_core.utils.database.base_models import BaseIDModel, with_read_session, with_session
from gsuid_core.webconsole.mount_app import GsAdminModel, PageSchema, site

T_MijiaUser = TypeVar("T_MijiaUser", bound="MijiaUser")


class MijiaUser(BaseIDModel, table=True):
    """机器人用户绑定的米家账号与完整登录凭据。"""

    __table_args__ = (
        UniqueConstraint("user_id", "mijia_user_id", name="uq_mijiauser_user_account"),
        {"extend_existing": True},
    )

    user_id: str = Field(index=True, title="机器人用户ID")
    mijia_user_id: str = Field(index=True, title="米家用户ID")
    auth_json: str = Field(default="", title="米家登录凭据JSON")
    is_default: bool = Field(default=False, title="是否默认账号")

    @classmethod
    @with_read_session
    async def get_by_user_id(
        cls: type[T_MijiaUser],
        session: AsyncSession,
        user_id: str,
    ) -> list[T_MijiaUser]:
        result = await session.execute(select(cls).where(col(cls.user_id) == user_id).order_by(col(cls.id)))
        return list(result.scalars().all())

    @classmethod
    @with_read_session
    async def get_default(
        cls: type[T_MijiaUser],
        session: AsyncSession,
        user_id: str,
    ) -> T_MijiaUser | None:
        result = await session.execute(
            select(cls).where(
                col(cls.user_id) == user_id,
                col(cls.is_default).is_(True),
            )
        )
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
        result = await session.execute(
            select(cls).where(
                col(cls.user_id) == user_id,
                col(cls.mijia_user_id) == mijia_user_id,
            )
        )
        row = result.scalars().first()
        await session.execute(update(cls).where(col(cls.user_id) == user_id).values(is_default=False))
        if row is None:
            session.add(
                cls(
                    user_id=user_id,
                    mijia_user_id=mijia_user_id,
                    auth_json=auth_json,
                    is_default=True,
                )
            )
            return

        row.auth_json = auth_json
        row.is_default = True
        session.add(row)

    @classmethod
    @with_session
    async def delete_default(
        cls: type[T_MijiaUser],
        session: AsyncSession,
        user_id: str,
    ) -> int:
        result = await session.execute(
            delete(cls).where(
                col(cls.user_id) == user_id,
                col(cls.is_default).is_(True),
            )
        )
        return result.rowcount if isinstance(result, CursorResult) else 0


class MijiaUserAdminModel(SQLModel, table=True):
    """控制台展示模型，仅映射非敏感列。"""

    __tablename__ = "mijiauser"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True, title="序号")
    user_id: str = Field(title="机器人用户ID")
    mijia_user_id: str = Field(title="米家用户ID")
    is_default: bool = Field(default=False, title="是否默认账号")


@site.register_admin
class MijiaUserAdmin(GsAdminModel):
    pk_name = "id"
    page_schema = PageSchema(label="米家账号", icon="fa fa-mobile")
    model = MijiaUserAdminModel

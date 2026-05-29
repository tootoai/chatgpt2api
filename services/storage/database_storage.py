from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, create_engine, func, inspect, or_, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from services.storage.base import StorageBackend

Base = declarative_base()


class AccountModel(Base):
    """账号数据模型"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_token = Column(String(2048), unique=True, nullable=False, index=True)
    email = Column(String(320), nullable=True, index=True)
    account_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=True, index=True)
    account_type = Column(String(64), nullable=False, default="free", index=True)
    status = Column(String(32), nullable=False, default="正常", index=True)
    quota = Column(Integer, nullable=False, default=0)
    image_quota_unknown = Column(Boolean, nullable=False, default=False)
    success = Column(Integer, nullable=False, default=0)
    fail = Column(Integer, nullable=False, default=0)
    image_lease_id = Column(String(64), nullable=True, index=True)
    created_at = Column(String(64), nullable=True, index=True)
    updated_at = Column(DateTime, nullable=True, server_default=text("CURRENT_TIMESTAMP"))
    data = Column(Text, nullable=False)  # JSON 格式存储完整账号数据


class AuthKeyModel(Base):
    """鉴权密钥数据模型"""
    __tablename__ = "auth_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_id = Column(String(255), unique=True, nullable=False, index=True)
    data = Column(Text, nullable=False)


class DatabaseStorageBackend(StorageBackend):
    """数据库存储后端（支持 SQLite、PostgreSQL、MySQL 等）"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,  # 自动检测连接是否有效
            pool_recycle=3600,   # 1小时回收连接
        )
        Base.metadata.create_all(self.engine)
        self._ensure_account_columns()
        self.Session = sessionmaker(bind=self.engine)

    def _ensure_account_columns(self) -> None:
        bool_default = "false" if self._is_postgres else "0"
        account_columns = {
            "email": "VARCHAR(320)",
            "account_id": "VARCHAR(255)",
            "user_id": "VARCHAR(255)",
            "account_type": "VARCHAR(64) DEFAULT 'free' NOT NULL",
            "status": "VARCHAR(32) DEFAULT '正常' NOT NULL",
            "quota": "INTEGER DEFAULT 0 NOT NULL",
            "image_quota_unknown": f"BOOLEAN DEFAULT {bool_default} NOT NULL",
            "success": "INTEGER DEFAULT 0 NOT NULL",
            "fail": "INTEGER DEFAULT 0 NOT NULL",
            "image_lease_id": "VARCHAR(64)",
            "created_at": "VARCHAR(64)",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }
        with self.engine.begin() as connection:
            existing = {
                column["name"]
                for column in inspect(connection).get_columns("accounts")
            }
            for column_name, column_type in account_columns.items():
                if column_name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE accounts ADD COLUMN {column_name} {column_type}"))
            for index_name, column_name in (
                ("idx_accounts_email", "email"),
                ("idx_accounts_account_id", "account_id"),
                ("idx_accounts_user_id", "user_id"),
                ("idx_accounts_account_type", "account_type"),
                ("idx_accounts_status", "status"),
                ("idx_accounts_image_lease_id", "image_lease_id"),
                ("idx_accounts_created_at", "created_at"),
            ):
                connection.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON accounts ({column_name})"))

    @property
    def _is_postgres(self) -> bool:
        return "postgresql" in self.database_url or "postgres" in self.database_url

    def load_accounts(self) -> list[dict[str, Any]]:
        """从数据库加载账号数据"""
        session = self.Session()
        try:
            accounts = []
            for row in session.query(AccountModel).all():
                account_data = self._row_account_data(row)
                if account_data is not None:
                    accounts.append(account_data)
            return accounts
        finally:
            session.close()

    def save_accounts(self, accounts: list[dict[str, Any]]) -> None:
        """保存账号数据到数据库"""
        self._save_rows(AccountModel, accounts, "access_token")

    def count_accounts(self) -> int:
        session = self.Session()
        try:
            return int(session.query(AccountModel).count())
        finally:
            session.close()

    def list_accounts_page(
        self,
        *,
        query: str = "",
        type_filter: str = "all",
        status_filter: str = "all",
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """用数据库分页账号，避免 10w 账号时每次把全量账号返回给前端。"""
        safe_limit = max(1, min(int(limit or 50), 500))
        safe_offset = max(0, int(offset or 0))
        normalized_query = str(query or "").strip()
        normalized_type = str(type_filter or "all").strip()
        normalized_status = str(status_filter or "all").strip()

        session = self.Session()
        try:
            rows = session.query(AccountModel)
            if normalized_query:
                pattern = f"%{normalized_query}%"
                rows = rows.filter(or_(AccountModel.email.ilike(pattern), AccountModel.access_token.ilike(pattern)))
            if normalized_type != "all":
                rows = rows.filter(AccountModel.account_type == normalized_type)
            if normalized_status != "all":
                rows = rows.filter(AccountModel.status == normalized_status)

            total = int(rows.count())
            page_rows = (
                rows.order_by(AccountModel.id.desc())
                .offset(safe_offset)
                .limit(safe_limit)
                .all()
            )
            items = [
                account
                for row in page_rows
                if (account := self._row_account_data(row)) is not None
            ]
            return {
                "items": items,
                "total": total,
                "limit": safe_limit,
                "offset": safe_offset,
                "stats": self.get_account_stats(session=session),
            }
        finally:
            session.close()

    def get_account_stats(self, *, session: Any | None = None) -> dict[str, Any]:
        own_session = session is None
        session = session or self.Session()
        try:
            def count_status(status: str) -> int:
                return int(session.query(func.count(AccountModel.id)).filter(AccountModel.status == status).scalar() or 0)

            total_quota = (
                session.query(func.coalesce(func.sum(AccountModel.quota), 0))
                .filter(AccountModel.status == "正常")
                .scalar()
            )
            total_success = session.query(func.coalesce(func.sum(AccountModel.success), 0)).scalar()
            total_fail = session.query(func.coalesce(func.sum(AccountModel.fail), 0)).scalar()
            by_type = {
                str(account_type or "unknown"): int(count or 0)
                for account_type, count in (
                    session.query(AccountModel.account_type, func.count(AccountModel.id))
                    .group_by(AccountModel.account_type)
                    .all()
                )
            }
            return {
                "total": int(session.query(func.count(AccountModel.id)).scalar() or 0),
                "active": count_status("正常"),
                "limited": count_status("限流"),
                "abnormal": count_status("异常"),
                "disabled": count_status("禁用"),
                "total_quota": int(total_quota or 0),
                "unlimited_quota_count": int(
                    session.query(func.count(AccountModel.id))
                    .filter(AccountModel.status == "正常")
                    .filter(AccountModel.image_quota_unknown.is_(True))
                    .scalar()
                    or 0
                ),
                "total_success": int(total_success or 0),
                "total_fail": int(total_fail or 0),
                "by_type": by_type,
            }
        finally:
            if own_session:
                session.close()

    def upsert_accounts(self, accounts: list[dict[str, Any]]) -> None:
        """按 access_token 增量写入账号，避免批量导入/更新时整表删除重写。"""
        clean_accounts = [
            account for account in accounts
            if isinstance(account, dict) and str(account.get("access_token") or "").strip()
        ]
        if not clean_accounts:
            return
        session = self.Session()
        try:
            tokens = [str(account.get("access_token") or "").strip() for account in clean_accounts]
            existing = {
                row.access_token: row
                for row in session.query(AccountModel).filter(AccountModel.access_token.in_(tokens)).all()
            }
            for account in clean_accounts:
                token = str(account.get("access_token") or "").strip()
                values = self._account_values(account)
                row = existing.get(token)
                if row is None:
                    session.add(AccountModel(**values))
                    continue
                for key, value in values.items():
                    setattr(row, key, value)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_accounts(self, access_tokens: list[str]) -> int:
        tokens = [str(token or "").strip() for token in dict.fromkeys(access_tokens) if str(token or "").strip()]
        if not tokens:
            return 0
        session = self.Session()
        try:
            removed = session.query(AccountModel).filter(AccountModel.access_token.in_(tokens)).delete(synchronize_session=False)
            session.commit()
            return int(removed or 0)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def delete_accounts_by_status(self, status: str) -> int:
        normalized_status = str(status or "").strip()
        if not normalized_status:
            return 0
        session = self.Session()
        try:
            removed = (
                session.query(AccountModel)
                .filter(AccountModel.status == normalized_status)
                .delete(synchronize_session=False)
            )
            session.commit()
            return int(removed or 0)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def load_auth_keys(self) -> list[dict[str, Any]]:
        """从数据库加载鉴权密钥数据"""
        return self._load_rows(AuthKeyModel)

    def save_auth_keys(self, auth_keys: list[dict[str, Any]]) -> None:
        """保存鉴权密钥数据到数据库"""
        self._save_rows(AuthKeyModel, auth_keys, "id", "key_id")

    def _load_rows(self, model: type[AccountModel] | type[AuthKeyModel]) -> list[dict[str, Any]]:
        session = self.Session()
        try:
            items = []
            for row in session.query(model).all():
                try:
                    item_data = json.loads(row.data)
                    if isinstance(item_data, dict):
                        items.append(item_data)
                except json.JSONDecodeError:
                    continue
            return items
        finally:
            session.close()

    @staticmethod
    def _row_account_data(row: AccountModel) -> dict[str, Any] | None:
        try:
            account_data = json.loads(row.data)
        except json.JSONDecodeError:
            return None
        return account_data if isinstance(account_data, dict) else None

    @staticmethod
    def _account_values(account: dict[str, Any]) -> dict[str, Any]:
        return {
            "access_token": str(account.get("access_token") or "").strip(),
            "email": str(account.get("email") or "").strip() or None,
            "account_id": str(account.get("account_id") or "").strip() or None,
            "user_id": str(account.get("user_id") or "").strip() or None,
            "account_type": str(account.get("type") or "free").strip() or "free",
            "status": str(account.get("status") or "正常").strip() or "正常",
            "quota": int(account.get("quota") or 0),
            "image_quota_unknown": bool(account.get("image_quota_unknown")),
            "success": int(account.get("success") or 0),
            "fail": int(account.get("fail") or 0),
            "image_lease_id": str(account.get("image_lease_id") or "").strip() or None,
            "created_at": str(account.get("created_at") or "").strip() or None,
            "data": json.dumps(account, ensure_ascii=False),
        }

    def _save_rows(
        self,
        model: type[AccountModel] | type[AuthKeyModel],
        items: list[dict[str, Any]],
        source_key: str,
        target_key: str | None = None,
    ) -> None:
        session = self.Session()
        try:
            session.query(model).delete()
            for item in items:
                if not isinstance(item, dict):
                    continue
                key_value = str(item.get(source_key) or "").strip()
                if not key_value:
                    continue
                if model is AccountModel:
                    session.add(model(**self._account_values(item)))
                else:
                    session.add(
                        model(
                            **{target_key or source_key: key_value},
                            data=json.dumps(item, ensure_ascii=False),
                        )
                    )
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def health_check(self) -> dict[str, Any]:
        """健康检查"""
        try:
            session = self.Session()
            try:
                # 尝试执行简单查询
                session.execute(text("SELECT 1"))
                count = session.query(AccountModel).count()
                auth_key_count = session.query(AuthKeyModel).count()
                return {
                    "status": "healthy",
                    "backend": "database",
                    "database_url": self._mask_password(self.database_url),
                    "account_count": count,
                    "auth_key_count": auth_key_count,
                }
            finally:
                session.close()
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": "database",
                "error": str(e),
            }

    def get_backend_info(self) -> dict[str, Any]:
        """获取存储后端信息"""
        db_type = "unknown"
        if "sqlite" in self.database_url:
            db_type = "sqlite"
        elif "postgresql" in self.database_url or "postgres" in self.database_url:
            db_type = "postgresql"
        elif "mysql" in self.database_url:
            db_type = "mysql"
        
        return {
            "type": "database",
            "db_type": db_type,
            "description": f"数据库存储 ({db_type})",
            "database_url": self._mask_password(self.database_url),
        }

    @staticmethod
    def _mask_password(url: str) -> str:
        """隐藏数据库连接字符串中的密码"""
        if "://" not in url:
            return url
        try:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                credentials, host = rest.split("@", 1)
                if ":" in credentials:
                    username, _ = credentials.split(":", 1)
                    return f"{protocol}://{username}:****@{host}"
            return url
        except Exception:
            return url

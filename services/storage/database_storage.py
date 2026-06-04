from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Column, String, Text, create_engine, Integer, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from services.storage.base import StorageBackend

Base = declarative_base()


class AccountModel(Base):
    """账号数据模型"""
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    access_token = Column(String(2048), unique=True, nullable=False, index=True)
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
        connect_args: dict[str, Any] = {}
        if database_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False, "timeout": 30}
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,  # 自动检测连接是否有效
            pool_recycle=3600,   # 1小时回收连接
            connect_args=connect_args,
        )
        Base.metadata.create_all(self.engine)
        if database_url.startswith("sqlite"):
            with self.engine.begin() as conn:
                conn.execute(text("PRAGMA journal_mode=WAL"))
                conn.execute(text("PRAGMA synchronous=NORMAL"))
                conn.execute(text("PRAGMA busy_timeout=30000"))
        self.Session = sessionmaker(bind=self.engine)

    def load_accounts(self) -> list[dict[str, Any]]:
        """从数据库加载账号数据"""
        session = self.Session()
        try:
            accounts = []
            for row in session.query(AccountModel).all():
                try:
                    account_data = json.loads(row.data)
                    if isinstance(account_data, dict):
                        accounts.append(account_data)
                except json.JSONDecodeError:
                    continue
            return accounts
        finally:
            session.close()

    def save_accounts(self, accounts: list[dict[str, Any]]) -> None:
        """保存账号数据到数据库"""
        self._save_rows(AccountModel, accounts, "access_token")

    def upsert_accounts(self, accounts: list[dict[str, Any]]) -> None:
        """增量新增或更新账号数据。"""
        self._upsert_rows(AccountModel, accounts, "access_token")

    def delete_accounts(self, access_tokens: list[str]) -> int:
        """按 access_token 增量删除账号。"""
        return self._delete_rows(AccountModel, "access_token", access_tokens)

    def replace_account(self, account: dict[str, Any], old_access_token: str | None = None) -> None:
        """保存单个账号；token 轮换时顺手删除旧 token 行。"""
        access_token = str(account.get("access_token") or "").strip()
        if not access_token:
            return
        session = self.Session()
        try:
            if old_access_token and old_access_token != access_token:
                session.query(AccountModel).filter(AccountModel.access_token == old_access_token).delete(
                    synchronize_session=False
                )
            self._upsert_row(session, AccountModel, account, "access_token")
            session.commit()
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

    def _upsert_rows(
        self,
        model: type[AccountModel] | type[AuthKeyModel],
        items: list[dict[str, Any]],
        source_key: str,
        target_key: str | None = None,
    ) -> None:
        session = self.Session()
        try:
            for item in items:
                self._upsert_row(session, model, item, source_key, target_key)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def _upsert_row(
        self,
        session,
        model: type[AccountModel] | type[AuthKeyModel],
        item: dict[str, Any],
        source_key: str,
        target_key: str | None = None,
    ) -> None:
        if not isinstance(item, dict):
            return
        key_value = str(item.get(source_key) or "").strip()
        if not key_value:
            return
        column_name = target_key or source_key
        row = session.query(model).filter(getattr(model, column_name) == key_value).one_or_none()
        data = json.dumps(item, ensure_ascii=False)
        if row is None:
            session.add(model(**{column_name: key_value}, data=data))
        else:
            row.data = data

    def _delete_rows(
        self,
        model: type[AccountModel] | type[AuthKeyModel],
        key_name: str,
        keys: list[str],
    ) -> int:
        cleaned = [str(key or "").strip() for key in keys]
        cleaned = list(dict.fromkeys(key for key in cleaned if key))
        if not cleaned:
            return 0
        session = self.Session()
        try:
            removed = 0
            column = getattr(model, key_name)
            for idx in range(0, len(cleaned), 500):
                chunk = cleaned[idx:idx + 500]
                removed += session.query(model).filter(column.in_(chunk)).delete(synchronize_session=False)
            session.commit()
            return int(removed)
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

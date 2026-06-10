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

    def count_accounts(self) -> int:
        session = self.Session()
        try:
            return int(session.query(AccountModel).count())
        finally:
            session.close()

    def delete_accounts_by_status(self, status: str) -> int:
        status_value = str(status or "").strip()
        if not status_value:
            return 0
        session = self.Session()
        try:
            tokens: list[str] = []
            for row in session.query(AccountModel.access_token, AccountModel.data).all():
                try:
                    account_data = json.loads(row.data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(account_data, dict):
                    continue
                if str(account_data.get("status") or "").strip() == status_value:
                    tokens.append(str(row.access_token))
            if not tokens:
                return 0
            removed = 0
            for idx in range(0, len(tokens), 500):
                chunk = tokens[idx:idx + 500]
                removed += session.query(AccountModel).filter(AccountModel.access_token.in_(chunk)).delete(
                    synchronize_session=False
                )
            session.commit()
            return int(removed)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def _account_status_category(item: dict[str, Any]) -> str:
        raw_status = str(item.get("status") or "").strip().lower()
        if raw_status in {"disabled", "\u7981\u7528"}:
            return "disabled"
        if raw_status in {"abnormal", "invalid", "error", "\u5f02\u5e38"}:
            return "abnormal"
        try:
            quota = int(item.get("quota") or 0)
        except (TypeError, ValueError):
            quota = 0
        image_quota_unknown = bool(item.get("image_quota_unknown"))
        if raw_status in {"limited", "\u9650\u6d41"} or (not image_quota_unknown and quota <= 0):
            return "limited"
        return "normal"

    @staticmethod
    def _status_filter_category(status: str) -> str:
        raw_status = str(status or "").strip().lower()
        aliases = {
            "": "all",
            "all": "all",
            "normal": "normal",
            "\u6b63\u5e38": "normal",
            "limited": "limited",
            "\u9650\u6d41": "limited",
            "abnormal": "abnormal",
            "invalid": "abnormal",
            "error": "abnormal",
            "\u5f02\u5e38": "abnormal",
            "disabled": "disabled",
            "\u7981\u7528": "disabled",
        }
        return aliases.get(raw_status, raw_status)

    @staticmethod
    def _account_matches_keyword(item: dict[str, Any], keyword: str) -> bool:
        if not keyword:
            return True
        text = keyword.lower()
        fields = (
            item.get("access_token"),
            item.get("accessToken"),
            item.get("email"),
            item.get("user_id"),
            item.get("account_id"),
            item.get("type"),
            item.get("plan_type"),
            item.get("source_type"),
            item.get("proxy"),
            item.get("group_id"),
        )
        return any(text in str(value or "").lower() for value in fields)

    def list_accounts_page(
        self,
        *,
        status_filter: str = "",
        keyword: str = "",
        group_id: str = "all",
        limit: int = 20,
        offset: int = 0,
    ) -> dict[str, Any]:
        items = self.load_accounts()
        status = self._status_filter_category(status_filter)
        keyword = str(keyword or "").strip()
        group_id = str(group_id or "all").strip()

        categories = [self._account_status_category(item) for item in items]
        stats = {
            "total": len(items),
            "active": sum(1 for category in categories if category == "normal"),
            "limited": sum(1 for category in categories if category == "limited"),
            "abnormal": sum(1 for category in categories if category == "abnormal"),
            "disabled": sum(1 for category in categories if category == "disabled"),
        }

        filtered: list[dict[str, Any]] = []
        for item in items:
            account_group_id = str(item.get("group_id") or "").strip()
            if group_id == "__ungrouped__":
                if account_group_id:
                    continue
            elif group_id and group_id != "all":
                if account_group_id != group_id:
                    continue
            if status != "all" and self._account_status_category(item) != status:
                continue
            if not self._account_matches_keyword(item, keyword):
                continue
            filtered.append(item)

        limit = max(1, min(500, int(limit or 20)))
        offset = max(0, int(offset or 0))
        return {
            "items": [dict(item) for item in filtered[offset:offset + limit]],
            "total": len(filtered),
            "all_total": len(items),
            "limit": limit,
            "offset": offset,
            "stats": stats,
        }

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

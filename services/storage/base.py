from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class StorageBackend(ABC):
    """抽象存储后端基类"""

    @abstractmethod
    def load_accounts(self) -> list[dict[str, Any]]:
        """加载所有账号数据"""
        pass

    @abstractmethod
    def save_accounts(self, accounts: list[dict[str, Any]]) -> None:
        """保存所有账号数据"""
        pass

    @staticmethod
    def _account_token(account: dict[str, Any]) -> str:
        return str(account.get("access_token") or account.get("accessToken") or "").strip()

    def upsert_accounts(self, accounts: list[dict[str, Any]]) -> None:
        current = list(self.load_accounts())
        index = {
            self._account_token(item): position
            for position, item in enumerate(current)
            if isinstance(item, dict) and self._account_token(item)
        }
        changed = False
        for account in accounts:
            if not isinstance(account, dict):
                continue
            token = self._account_token(account)
            if not token:
                continue
            if token in index:
                current[index[token]] = account
            else:
                index[token] = len(current)
                current.append(account)
            changed = True
        if changed:
            self.save_accounts(current)

    def delete_accounts(self, access_tokens: list[str]) -> int:
        target_tokens = {str(token or "").strip() for token in access_tokens if str(token or "").strip()}
        if not target_tokens:
            return 0
        accounts = self.load_accounts()
        next_accounts = [
            item for item in accounts
            if self._account_token(item) not in target_tokens
        ]
        removed = len(accounts) - len(next_accounts)
        if removed:
            self.save_accounts(next_accounts)
        return removed

    @abstractmethod
    def load_auth_keys(self) -> list[dict[str, Any]]:
        """加载所有鉴权密钥数据"""
        pass

    @abstractmethod
    def save_auth_keys(self, auth_keys: list[dict[str, Any]]) -> None:
        """保存所有鉴权密钥数据"""
        pass

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """健康检查，返回存储后端状态"""
        pass

    @abstractmethod
    def get_backend_info(self) -> dict[str, Any]:
        """获取存储后端信息"""
        pass

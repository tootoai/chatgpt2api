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

    def count_accounts(self) -> int:
        return len(self.load_accounts())

    def delete_accounts_by_status(self, status: str) -> int:
        status_value = str(status or "").strip()
        if not status_value:
            return 0
        accounts = self.load_accounts()
        kept = [
            item
            for item in accounts
            if str(item.get("status") or "").strip() != status_value
        ]
        removed = len(accounts) - len(kept)
        if removed:
            self.save_accounts(kept)
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

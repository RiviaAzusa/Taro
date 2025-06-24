import os
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Config:
    """配置类，从yaml文件加载配置"""

    # 基础配置项
    db_file: str = "resources/db/taro.db"
    kb_folder: str = "resources/kb"
    log_level: str = "INFO"

    # 可选的其他配置项
    app_name: str = "Taro"
    debug: bool = False

    @classmethod
    def load_from_yaml(
        cls, config_path: Optional[str] = None, env: str = "dev"
    ) -> "Config":
        """
        从yaml文件加载配置

        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
            env: 环境名称，默认为dev

        Returns:
            Config实例
        """
        if config_path is None:
            # 获取项目根目录
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "resources" / "configs" / f"{env}.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            print(f"警告: 配置文件 {config_path} 不存在，使用默认配置")
            return cls()

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"警告: 加载配置文件失败 {e}，使用默认配置")
            return cls()

        # 创建配置实例
        config = cls()

        # 更新配置项
        for key, value in config_data.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                print(f"警告: 未知的配置项 {key}")

        return config

    def save_to_yaml(self, config_path: str) -> None:
        """
        保存配置到yaml文件

        Args:
            config_path: 配置文件路径
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config_dict = {
            "db_file": self.db_file,
            "kb_folder": self.kb_folder,
            "log_level": self.log_level,
            "app_name": self.app_name,
            "debug": self.debug,
        }

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)

    def validate(self) -> bool:
        """
        验证配置是否有效

        Returns:
            配置是否有效
        """
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

        if self.log_level not in valid_log_levels:
            print(f"错误: log_level必须是 {valid_log_levels} 中的一个")
            return False

        if not self.db_file:
            print("错误: db_file不能为空")
            return False

        if not self.kb_folder:
            print("错误: kb_folder不能为空")
            return False

        return True

    def ensure_directories(self) -> None:
        """确保必要的目录存在"""
        # 确保数据库文件目录存在
        db_dir = Path(self.db_file).parent
        db_dir.mkdir(parents=True, exist_ok=True)

        # 确保知识库目录存在
        kb_dir = Path(self.kb_folder)
        kb_dir.mkdir(parents=True, exist_ok=True)


# 全局配置实例
config = Config.load_from_yaml()


def get_config(env: str = "dev") -> Config:
    """
    获取配置实例

    Args:
        env: 环境名称

    Returns:
        Config实例
    """
    return Config.load_from_yaml(env=env)


def reload_config(env: str = "dev") -> Config:
    """
    重新加载配置

    Args:
        env: 环境名称

    Returns:
        新的Config实例
    """
    global config
    config = Config.load_from_yaml(env=env)
    return config
